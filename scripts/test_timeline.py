import copy
import unittest
from timeline import compile_timeline


class TimelineTests(unittest.TestCase):
    def setUp(self):
        self.spec = {'fps':30,'source_frames':120,'clips':[
            {'id':'a','source_start':0,'duration':30},
            {'id':'proof','source_start':60,'duration':30},
            {'id':'b','source_start':30,'duration':90}],
            'captions':[{'start':20,'end':40,'text':'cross cut'}, {'start':60,'end':80,'text':'proof'}],
            'avatars':[{'id':'host','path':'host.mp4','source_start':60,'duration':30,'media_frames':30}]}

    def test_insert_rebases_all_tracks(self):
        out=compile_timeline(self.spec)
        self.assertEqual(out['duration'],150)
        self.assertEqual([x['start'] for x in out['avatars']],[30,90])
        self.assertEqual([(x['start'],x['end']) for x in out['captions']],[(20,30),(30,50),(60,70),(90,110)])

    def test_trim_keeps_avatar_media_offset(self):
        self.spec['clips']=[{'id':'trim','source_start':70,'duration':10}]
        a=compile_timeline(self.spec)['avatars'][0]
        self.assertEqual((a['start'],a['duration'],a['media_start']),(0,10,10))

    def test_no_silent_loop(self):
        self.spec['avatars'][0]['media_frames']=29
        with self.assertRaises(ValueError):compile_timeline(self.spec)

    def test_overlap_and_invalid_frames(self):
        for mutation in ('duplicate','overflow','fraction','caption_overlap','avatar_overlap'):
            s=copy.deepcopy(self.spec)
            if mutation=='duplicate':s['clips'][1]['id']='a'
            if mutation=='overflow':s['clips'][0]['duration']=121
            if mutation=='fraction':s['clips'][0]['duration']=3.5
            if mutation=='caption_overlap':s['captions'][1]['start']=39
            if mutation=='avatar_overlap':s['avatars'].append({**s['avatars'][0],'id':'other'})
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):compile_timeline(s)

if __name__=='__main__':unittest.main()
