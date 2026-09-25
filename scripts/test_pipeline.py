"""Behavioral tests using synthetic artifacts, no external calls."""
import argparse
import copy
import tempfile
import unittest
from pathlib import Path
import pipeline as p


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.data = {'modules': {k: {'status': 'not_started'} for k in p.DEPS}, 'history': []}
        self.source = self.root / 'source.txt'
        self.source.write_text('test', encoding='utf-8')
        self.evidence = self.root / 'review.json'
        self.evidence.write_text('{"verdict":"pass","reviewer":"synthetic-test","checked_at":"2026-09-20","checks":["fixture"]}', encoding='utf-8')

    def tearDown(self):
        self.tmp.cleanup()

    def action(self, command, module, **kwargs):
        args = dict(command=command, module=module, input=[str(self.source)], output=[], executor='test',
                    version='1', imported=False, evidence=str(self.evidence), reason='test')
        args.update(kwargs)
        p.mutate(self.data, argparse.Namespace(**args))

    def finish(self, module, imported=False):
        output = self.root / (module + '.txt')
        output.write_text(module, encoding='utf-8')
        self.action('record', module, output=[str(output)], imported=imported)
        self.action('validate', module)

    def test_full_chain_and_style_invalidation(self):
        for m in p.DEPS:
            self.finish(m)
        self.action('invalidate', 'packaging')
        states = p.statuses(self.data)
        self.assertEqual(states['voice'], 'validated')
        self.assertEqual(states['avatar'], 'validated')
        self.assertEqual(states['qc'], 'stale')

    def test_import_video_skips_paid_generation(self):
        self.finish('avatar', imported=True)
        self.assertEqual(p.statuses(self.data)['captions'], 'ready')
        self.action('invalidate', 'script')
        self.assertEqual(p.statuses(self.data)['avatar'], 'validated')

    def test_input_change_propagates(self):
        for m in p.DEPS:
            self.finish(m)
        self.source.write_text('changed', encoding='utf-8')
        self.assertTrue(all(s == 'stale' for s in p.statuses(self.data).values()))

    def test_missing_output_and_failed_evidence(self):
        with self.assertRaises(ValueError):
            self.action('record', 'script', output=[str(self.root / 'missing')])
        self.finish('script')
        self.evidence.write_text('{}', encoding='utf-8')
        self.assertEqual(p.statuses(self.data)['script'], 'stale')

    def test_dependencies_and_provider_recovery(self):
        with self.assertRaises(ValueError):
            self.finish('avatar')
        self.finish('script')
        self.action('job', 'voice', job_id='job1', provider_status='unknown')
        with self.assertRaises(ValueError):
            self.action('job', 'voice', job_id='job2', provider_status='pending')
        self.action('job', 'voice', job_id='job1', provider_status='succeeded')
        self.assertEqual(p.statuses(self.data)['voice'], 'running')

    def test_output_tampering(self):
        self.finish('script')
        (self.root / 'script.txt').write_text('tampered', encoding='utf-8')
        self.assertEqual(p.statuses(self.data)['voice'], 'stale')

    def test_narration_does_not_require_full_avatar(self):
        self.data['mode']='narration'
        self.finish('script'); self.finish('voice')
        self.assertEqual(p.statuses(self.data)['captions'],'ready')
        self.finish('captions'); self.finish('assets'); self.finish('packaging')
        self.assertEqual(p.statuses(self.data)['avatar'],'ready')

    def test_v2_rejects_unbound_review(self):
        self.data['schema_version']=2
        with self.assertRaises(ValueError):self.finish('script')

    def test_v2_review_binds_exact_output(self):
        import json
        self.data['schema_version']=2
        out=self.root/'checked.txt'; out.write_text('checked')
        self.action('record','script',output=[str(out)])
        evidence={'verdict':'pass','reviewer':'test','checked_at':'2026-09-25',
                  'checks':['content'],'artifacts':[p.file_record(out)]}
        self.evidence.write_text(json.dumps(evidence))
        self.action('validate','script')
        self.assertEqual(p.statuses(self.data)['script'],'validated')


if __name__ == '__main__':
    unittest.main()
