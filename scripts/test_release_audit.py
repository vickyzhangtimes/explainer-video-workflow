import tempfile,unittest
from pathlib import Path
from release_audit import check_file

class AuditTests(unittest.TestCase):
 def test_secrets_and_traversal(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);p=root/'sample.txt'
   p.write_text('ordinary tutorial text');self.assertEqual(check_file(root,'sample.txt'),[])
   p.write_text('sk-'+'x'*24);self.assertTrue(check_file(root,'sample.txt'))
   self.assertTrue(check_file(root,'../outside.txt'))
   self.assertTrue(check_file(root,'.env'))
 def test_binary_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'photo.png';p.write_bytes(b'fake');self.assertTrue(check_file(Path(d),'photo.png'))

if __name__=='__main__':unittest.main()
