"""Compile source-frame edits, captions and avatar ranges onto one output clock.

No network, inference, interpolation of missing word times, or media mutation.
All intervals are [start, end); all times are integer frames at the specified fps.
"""
import argparse
import json
from pathlib import Path


def integer(value, name, minimum=0):
    if type(value) is not int or value < minimum:
        raise ValueError(f'{name} must be an integer >= {minimum}')
    return value


def compile_timeline(spec):
    fps = integer(spec['fps'], 'fps', 1)
    source_frames = integer(spec['source_frames'], 'source_frames', 1)
    clips, cursor, ids = [], 0, set()
    for item in spec['clips']:
        ident = item['id']
        if not isinstance(ident, str) or not ident or ident in ids:
            raise ValueError('Clip IDs must be unique nonempty strings')
        ids.add(ident)
        start = integer(item['source_start'], 'source_start')
        duration = integer(item['duration'], 'duration', 1)
        if start + duration > source_frames:
            raise ValueError(f'{ident}: source range exceeds audio')
        clips.append({**item, 'output_start': cursor})
        cursor += duration
    if not clips:
        raise ValueError('At least one clip required')
    cues = spec.get('captions', [])
    previous_end = 0
    for cue in cues:
        start, end = integer(cue['start'], 'caption start'), integer(cue['end'], 'caption end', 1)
        if start < previous_end or end <= start or end > source_frames or not cue.get('text'):
            raise ValueError('Captions must be ordered, non-overlapping, nonempty and in bounds')
        previous_end = end
    avatars = spec.get('avatars', [])
    avatar_ids = set()
    for avatar in avatars:
        if avatar['id'] in avatar_ids:
            raise ValueError('Duplicate avatar ID')
        avatar_ids.add(avatar['id'])
        start = integer(avatar['source_start'], 'avatar source_start')
        duration = integer(avatar['duration'], 'avatar duration', 1)
        if start + duration > source_frames or duration > integer(avatar['media_frames'], 'media_frames', 1):
            raise ValueError('Avatar range exceeds source or actual media; do not loop missing lips')
    output_captions, output_avatars = [], []
    for clip in clips:
        start, end = clip['source_start'], clip['source_start'] + clip['duration']
        for cue in cues:
            a, b = max(start, cue['start']), min(end, cue['end'])
            if b > a:
                output_captions.append({'start': clip['output_start'] + a - start,
                    'end': clip['output_start'] + b - start, 'text': cue['text'],
                    'source_start': a, 'clip_id': clip['id']})
        for avatar in avatars:
            if not clip.get('include_avatars', True):
                continue
            a, b = max(start, avatar['source_start']), min(end, avatar['source_start'] + avatar['duration'])
            if b > a:
                output_avatars.append({'id': avatar['id'], 'path': avatar['path'],
                    'start': clip['output_start'] + a - start, 'duration': b - a,
                    'media_start': a - avatar['source_start'], 'clip_id': clip['id']})
    ordered = sorted(output_avatars, key=lambda a: a['start'])
    if any(b['start'] < a['start'] + a['duration'] for a,b in zip(ordered, ordered[1:])):
        raise ValueError('Avatar overlays overlap; choose one active speaker')
    return {'schema_version': 1, 'fps': fps, 'duration': cursor,
            'clips': clips, 'captions': output_captions, 'avatars': ordered}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input'); parser.add_argument('output')
    args = parser.parse_args()
    result = compile_timeline(json.loads(Path(args.input).read_text(encoding='utf-8-sig')))
    Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"Compiled {len(result['clips'])} clips; {result['duration']} frames")


if __name__ == '__main__':
    main()
