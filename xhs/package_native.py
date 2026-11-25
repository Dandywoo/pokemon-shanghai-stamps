from pathlib import Path
import base64,json,re,zipfile
root=Path('dist-native')
(root/'images').mkdir(parents=True,exist_ok=True)
h=Path('xhs/index.html').read_text()
j=Path('xhs/app.source.js').read_text()
m=re.search(r'const LOCAL_ART\s*=\s*(\{.*?\});',j,re.S)
assert m
art=json.loads(m.group(1))
assert len(art)==30
paths={}
for key,data in art.items():
    assert re.fullmatch(r'\d+',key)
    mime,b64=data.split(',',1)
    assert mime=='data:image/png;base64'
    raw=base64.b64decode(b64,validate=True)
    assert raw[:8]==b'\x89PNG\r\n\x1a\n'
    path='images/'+key+'.png'
    (root/path).write_bytes(raw)
    paths[key]='./'+path
j=j[:m.start(1)]+json.dumps(paths,separators=(',',':'))+j[m.end(1):]
def image(m):
    ext=m.group(1).replace('jpeg','jpg')
    path='images/shanghai-30-header.'+ext
    (root/path).write_bytes(base64.b64decode(m.group(2),validate=True))
    return './'+path
h,n=re.subn(r'data:image/(webp|jpeg|png);base64,([A-Za-z0-9+/=]+)',image,h)
assert n==1,n
assert 'V5.6.23' in h and 'districtCandidates' in h and 'BUS_PATTERNS' in j
assert len(re.findall(r'<script\b',h))==1 and '<script defer src="./app.js"></script>' in h
for forbidden in ['localStorage','navigator.geolocation','navigator.share','navigator.clipboard','window.open','document.execCommand','URL.createObjectURL','raw.githubusercontent.com']:
    assert forbidden not in j,forbidden
assert not re.search(r'\b(?:src|href)=["\x27]https?://',h)
assert not re.search(r'\son[a-z]+=',h,re.I)
(root/'index.html').write_text(h)
(root/'app.source.js').write_text(j)
