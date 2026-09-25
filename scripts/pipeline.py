"""Local artifact ledger. Never submits provider jobs or executes a renderer."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import sys
from datetime import datetime, timezone

DEPS = {
    'script': [], 'voice': ['script'], 'avatar': ['voice'],
    'captions': ['avatar'], 'assets': ['script'],
    'packaging': ['avatar', 'captions', 'assets'],
    'render': ['packaging'], 'qc': ['render'],
}
NARRATION_DEPS = {**DEPS, 'captions': ['voice'],
                  'packaging': ['voice', 'captions', 'assets']}


def dependencies(data):
    # Old ledgers retain their original dependency semantics.
    return NARRATION_DEPS if data.get('mode') == 'narration' else DEPS
RUN_DIRS = ('01-brief', '02-script', '03-voice', '04-avatar', '05-captions',
            '06-assets', '07-packaging', '08-render', '09-qc', '10-deliverables')


def now():
    return datetime.now(timezone.utc).isoformat()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def file_record(path):
    path = Path(path).resolve()
    if not path.is_file() or path.stat().st_size == 0:
        raise ValueError(f'Missing or empty file: {path}')
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return {'path': str(path), 'sha256': digest.hexdigest()}


def unchanged(record):
    try:
        return file_record(record['path']) == record
    except (ValueError, OSError):
        return False


def statuses(data):
    result = {}
    for key, deps in dependencies(data).items():
        entry = data['modules'][key]
        if entry['status'] == 'stale':
            result[key] = 'stale'
            continue
        records = entry.get('inputs', []) + entry.get('outputs', [])
        if entry.get('evidence'):
            records += [entry['evidence']]
        if any(not unchanged(record) for record in records):
            result[key] = 'stale'
            continue
        if not entry.get('imported'):
            changed_deps = any(data['modules'][d].get('outputs', []) != expected
                               for d, expected in entry.get('dependency_outputs', {}).items())
            if changed_deps or any(result[d] == 'stale' for d in deps):
                result[key] = 'stale'
                continue
            if any(result[d] != 'validated' for d in deps):
                result[key] = 'blocked'
                continue
        result[key] = 'ready' if entry['status'] == 'not_started' else entry['status']
    return result


def invalidate(data, module, reason):
    affected = {module}
    for key, deps in dependencies(data).items():
        # Imported files are explicit new roots: unrelated upstream changes stop here.
        if key != module and not data['modules'][key].get('imported') and affected.intersection(deps):
            affected.add(key)
    for key in affected:
        if key == module or data['modules'][key]['status'] != 'not_started':
            data['modules'][key]['status'] = 'stale'
            data['modules'][key]['stale_reason'] = reason


def mutate(data, args):
    module = args.module
    entry = data['modules'][module]
    effective = statuses(data)
    if args.command == 'invalidate':
        invalidate(data, module, args.reason)
    elif args.command == 'record':
        if not args.imported and any(effective[d] != 'validated' for d in dependencies(data)[module]):
            raise ValueError('Upstream modules must be validated; use --imported only for independent existing assets')
        inputs = [file_record(p) for p in args.input]
        outputs = [file_record(p) for p in args.output]
        # Preserve downstream invalidation even if replacement output has identical bytes.
        invalidate(data, module, 'upstream record replaced')
        data['modules'][module] = {
            'status': 'generated', 'inputs': inputs, 'outputs': outputs,
            'executor': args.executor, 'tool_version': args.version,
            'imported': args.imported, 'recorded_at': now(),
            'jobs': entry.get('jobs', []),
            'dependency_outputs': {} if args.imported else {
                d: copy.deepcopy(data['modules'][d].get('outputs', [])) for d in dependencies(data)[module]},
        }
    elif args.command == 'validate':
        if effective[module] != 'generated':
            raise ValueError('Only generated, unchanged artifacts may be validated')
        evidence = read(args.evidence)
        if (evidence.get('verdict') != 'pass' or not evidence.get('reviewer')
                or not evidence.get('checked_at') or not isinstance(evidence.get('checks'), list)
                or not evidence['checks']):
            raise ValueError('Evidence requires verdict=pass, reviewer, checked_at and nonempty checks')
        if data.get('schema_version', 1) >= 2:
            if evidence.get('artifacts') != entry.get('outputs'):
                raise ValueError('Review must bind all exact output paths and hashes')
            if module == 'qc' and not all(evidence.get('coverage', {}).get(k) is True
                    for k in ('technical', 'visual', 'audiovisual')):
                raise ValueError('Final QC requires technical, visual and audiovisual coverage')
        entry.update(status='validated', evidence=file_record(args.evidence))
    elif args.command == 'job':
        if module not in ('voice', 'avatar'):
            raise ValueError('Provider job tracking is only for voice/avatar')
        if any(effective[d] != 'validated' for d in dependencies(data)[module]):
            raise ValueError('Validate upstream before tracking a provider job')
        jobs = entry.setdefault('jobs', [])
        existing = next((j for j in jobs if j['id'] == args.job_id), None)
        if not existing and any(j['provider_status'] in ('pending', 'running', 'unknown') for j in jobs):
            raise ValueError('Unresolved provider job exists; recover its ID before tracking another')
        if existing is None:
            existing = {'id': args.job_id}
            jobs.append(existing)
        existing.update(provider_status=args.provider_status, checked_at=now())
        # Preserve generated/validated artifacts when merely recording a query.
        if entry['status'] not in ('generated', 'validated', 'stale'):
            entry['status'] = 'failed' if args.provider_status == 'failed' else 'running'
    data['history'].append({'at': now(), 'action': args.command, 'module': module})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['init', 'plan', 'record', 'validate', 'invalidate', 'job'])
    parser.add_argument('--run', required=True)
    parser.add_argument('--profile', help='Existing reusable asset profile JSON; init only')
    parser.add_argument('--mode', choices=['full-avatar', 'narration'], default='narration')
    parser.add_argument('--module', choices=list(DEPS))
    parser.add_argument('--input', action='append', default=[])
    parser.add_argument('--output', action='append', default=[])
    parser.add_argument('--executor')
    parser.add_argument('--version')
    parser.add_argument('--imported', action='store_true')
    parser.add_argument('--evidence')
    parser.add_argument('--reason')
    parser.add_argument('--job-id')
    parser.add_argument('--provider-status', choices=['pending', 'running', 'succeeded', 'failed', 'unknown'])
    args = parser.parse_args()
    path = Path(args.run).resolve() / 'pipeline.json'
    if args.command == 'init':
        profile = None
        if args.profile:
            profile_data = read(args.profile)
            if not profile_data.get('profile_id'):
                raise ValueError('Asset profile requires profile_id')
            profile = file_record(args.profile)
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {'schema_version': 2, 'mode': args.mode, 'created_at': now(), 'modules': {
            key: {'status': 'not_started'} for key in DEPS}, 'history': []}
        data['asset_profile'] = profile
        with path.open('x', encoding='utf-8') as stream:
            json.dump(data, stream, ensure_ascii=False, indent=2)
        for directory in RUN_DIRS:
            (path.parent / directory).mkdir(exist_ok=True)
    else:
        data = read(path)
        if args.command == 'plan':
            result = statuses(data)
            print(json.dumps({'asset_profile_changed': bool(data.get('asset_profile')) and not unchanged(data['asset_profile']),
                  'modules': result, 'next': next((k for k,v in result.items()
                  if v in ('ready', 'generated', 'running', 'failed', 'stale')), None)}, ensure_ascii=False, indent=2))
            return
        if not args.module:
            raise ValueError('--module required')
        required = {'record': ['input', 'output', 'executor', 'version'],
                    'validate': ['evidence'], 'invalidate': ['reason'],
                    'job': ['job_id', 'provider_status']}[args.command]
        if any(not getattr(args, key) for key in required):
            raise ValueError('Required: ' + ', '.join(required))
        previous = copy.deepcopy(data['modules'])
        mutate(data, args)
        data['history'][-1]['before'] = previous
        # Atomic replacement; single writer per run (documented).
        temp = path.with_suffix('.json.tmp')
        with temp.open('x', encoding='utf-8') as stream:
            json.dump(data, stream, ensure_ascii=False, indent=2)
        temp.replace(path)
    print(str(path))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, KeyError, json.JSONDecodeError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
