import csv, io, json, re, shutil, urllib.request, zipfile, concurrent.futures
from pathlib import Path
from PIL import Image
root=Path('dist-xhs')
src=Path('xhs/app.source.js').read_text()
venues=json.loads(re.search(r'^const V=(.*);$',src,re.M).group(1))
dex=json.loads(re.search(r'^const DEX=(.*);$',src,re.M).group(1))
names={it['id']:it['stamp'] for v in venues for it in v['items']}
assert len(names)==len(dex)==len(set(dex.values()))==30
assert set(names)==set(dex)
def fetch(url):
    for attempt in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Shanghai-Collection-Preview/1.0'}),timeout=25) as r:
                return r.read()
        except Exception:
            if attempt==2: raise
base='https://raw.githubusercontent.com/PokeAPI/pokeapi/master/data/v2/csv/'
rows=csv.DictReader(io.StringIO(fetch(base+'pokemon_species_names.csv').decode('utf-8-sig')))
cn={int(r['pokemon_species_id']):r['name'] for r in rows if r['local_language_id']=='12'}
for id,n in dex.items():
    assert cn.get(n)==names[id], (id,n,cn.get(n),names[id])
print('30 of 30 names match simplified Chinese PokéAPI species dataset')
assert dex['s2-1']==976
out=Path('dist-silhouette')
shutil.copytree(root,out,dirs_exist_ok=True)
assets=out/'assets'
assets.mkdir(exist_ok=True)
def silhouette(n):
    data=fetch(f'https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/{n}.png')
    im=Image.open(io.BytesIO(data)).convert('RGBA')
    alpha=im.getchannel('A')
    assert alpha.getextrema()[0]==0 and alpha.getextrema()[1]>200, n
    im=im.crop(alpha.getbbox())
    im.thumbnail((192,192),Image.Resampling.LANCZOS)
    result=Image.new('RGBA',im.size,(0,0,0,0))
    result.putalpha(im.getchannel('A'))
    result.save(assets/f'{n}.png',optimize=True)
with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
    list(ex.map(silhouette,dex.values()))
assert len(list(assets.glob('*.png')))==30
p=out/'app.js'
js=p.read_text()
old=re.search(r'function dexArt\(id\)\s*\{[^}]*\}',js)
assert old
js=js[:old.start()]+'''function dexArt(id) { return '<span class="dex-art"><span class="dex-fallback">'+dexNo(id)+'</span><img alt="" loading="lazy" src="./assets/'+DEX[id]+'.png" data-dex-art></span>'; }'''+js[old.end():]
p.write_text(js)
p=out/'index.html'
html=p.read_text().replace('当前适配预览采用原创编号牌，角色素材须获相应授权后方可加入。','剪影取自 PokéAPI 公开图像源并作单色处理；角色相关权利归原权利人，公开发布前须确认授权。')
p.write_text(html)
def package(folder,name):
    with zipfile.ZipFile(name,'w',zipfile.ZIP_DEFLATED) as z:
        for p in sorted(folder.rglob('*')):
            if p.is_file(): z.write(p,p.relative_to(folder))
    with zipfile.ZipFile(name) as z:
        assert z.testzip() is None
        assert 'index.html' in z.namelist() and 'app.js' in z.namelist()
        print(name,len(z.namelist()),Path(name).stat().st_size)
package(root,'shanghai-dex-xhs-number-verified.zip')
package(out,'shanghai-dex-xhs-silhouette.zip')
Path('dex-verification.csv').write_text('全国图鉴编号,宝可梦,官方图鉴页面\n'+'\n'.join(f'{n:04d},{names[id]},https://dex.pokemon.cn/play/pokedex/{n:04d}' for id,n in sorted(dex.items(),key=lambda p:p[1]))+'\n',encoding='utf-8-sig')
