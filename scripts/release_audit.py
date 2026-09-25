"""Audit an explicit text-only publication list. Does not prove legal clearance."""
import json,re,subprocess,sys
from pathlib import Path

PATTERNS=[r'sk-[A-Za-z0-9_-]{16,}',r'gh[pousr]_[A-Za-z0-9_]{20,}',
          r'github_pat_[A-Za-z0-9_]{20,}',r'-----BEGIN [A-Z ]*PRIVATE KEY',
          r'(?i)(?:signature|x-oss-signature|x-amz-signature|security-token)=[A-Za-z0-9%/+_-]{10,}',
          r'(?i)[A-Z]:[/\\](?:Users|我的经历|连接需要|vicky-ai-system)[/\\]',
          r'/Us' + r'ers/[^/\s]+/',r'(?i)Bearer\s+[A-Za-z0-9._-]{20,}']

def check_file(root,relative):
    path=root/relative
    if path.is_symlink() or root.resolve() not in path.resolve().parents:
        return ['link or path outside root']
    if any(part.startswith('.') and part not in ('.gitignore','.github') for part in Path(relative).parts):
        return ['unexpected hidden file']
    if path.suffix.lower() in ('.pem','.key','.mp4','.wav','.mp3','.png','.jpg','.zip'):
        return ['private or binary asset not allowed in this release']
    try:text=path.read_text(encoding='utf-8')
    except (OSError,UnicodeError):return ['missing or non-text file']
    return [f'pattern {i+1}' for i,p in enumerate(PATTERNS) if re.search(p,text)]

def audit(root):
    names=json.loads((root/'RELEASE_FILES.json').read_text(encoding='utf-8'))
    if len(names)!=len(set(names)):raise ValueError('Duplicate public path')
    issues={n:check_file(root,n) for n in names}
    issues={n:v for n,v in issues.items() if v}
    if (root/'.git').exists():
        tracked=subprocess.check_output(['git','ls-files','-z'],cwd=root).decode().split('\0')
        for name in filter(None,tracked):
            if name not in names:issues[name]=['tracked but absent from release list']
    if issues:raise ValueError(json.dumps(issues,ensure_ascii=False))
    return names

if __name__=='__main__':
    try:print(f'PASS: {len(audit(Path(__file__).resolve().parents[1]))} explicitly listed text files')
    except (ValueError,OSError) as e:print(str(e),file=sys.stderr);sys.exit(1)
