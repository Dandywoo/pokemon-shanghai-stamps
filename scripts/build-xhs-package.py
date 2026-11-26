from pathlib import Path
from io import BytesIO
import base64, json, re, shutil
from PIL import Image

source=Path("index.html").read_text(encoding="utf-8")
assert "window.__dexVersion='7.2.2'" in source
assert 'href="game-theme.css?v=3"' in source
scripts=re.findall(r'<script\b[^>]*>([\s\S]*?)</script>',source,re.I)
assert len(scripts)==1
js=scripts[0]
html=re.sub(r'<script\b[^>]*>[\s\S]*?</script>', '<script src="./app.js"></script>',source,count=1,flags=re.I)
html=html.replace('href="game-theme.css?v=3"','href="./game-theme.css"')
def replace(a,b,count=1):
    global js
    assert js.count(a)==count, (a[:120],js.count(a),count)
    js=js.replace(a,b)
# Keep the existing native storage key and schema, including extra route preferences.
replace('draft: a.draft && typeof a.draft === "object" ? a.draft : {},', '''draft: a.draft && typeof a.draft === "object" ? a.draft : {}, manualRoute: a.manualRoute && typeof a.manualRoute === "object" ? a.manualRoute : {}, achievementGoals: Array.isArray(a.achievementGoals) ? a.achievementGoals.filter(Number.isInteger).slice(0,100) : [],''')
a=js.index('if(!x){try{const raw=localStorage')
b=js.index('mini = x && x.miniTool;',a)
js=js[:a]+"""if(!x||!x.miniTool){storageStatus('本次无法保存进度，请使用文本备份。');return;}
        """+js[b:]
replace("JSON.parse(localStorage.getItem('sh-pokemon-stamps-v7-ach')||'[]')","(state.achievementGoals||[])")
replace("localStorage.setItem('sh-pokemon-stamps-v7-ach',JSON.stringify([...window.__v7Goals]))","state.achievementGoals=[...window.__v7Goals];save()")
replace("JSON.parse(localStorage.getItem('sh-pokemon-stamps-manual-route-v1')||'null')","(state.manualRoute||null)",2)
replace("localStorage.setItem('sh-pokemon-stamps-manual-route-v1',JSON.stringify({active:window.manualMode,ids:[...window.manualVenues],goal:window.manualGoal,goalMode:window.manualGoalMode}))","const draft={active:window.manualMode,ids:[...window.manualVenues],goal:window.manualGoal,goalMode:window.manualGoalMode};if(JSON.stringify(state.manualRoute)!==JSON.stringify(draft)){state.manualRoute=draft;save()}")
# Replace browser location only at the input boundary, preserving the candidate/route algorithm.
replace("""if(!navigator.geolocation)throw Error('浏览器不支持定位，请手动选择。');
  const p=await new Promise((ok,no)=>navigator.geolocation.getCurrentPosition(ok,no,{enableHighAccuracy:true,timeout:12000,maximumAge:0}));""","""const api=window.xhs&&window.xhs.miniTool;
  if(!api||typeof api.getLocation!=='function'||clientVersion===null||clientVersion<9490)throw Error('请升级小红书至9.49或手动选择起点。');
  const native=await timed(api.getLocation({type:'wgs84'}),20000);
  if(!native||native.errMsg!=='getLocation:ok'||!Number.isFinite(native.latitude)||!Number.isFinite(native.longitude)||Math.abs(native.latitude)>90||Math.abs(native.longitude)>180)throw Error('定位失败，请手动选择。');
  const p={coords:{latitude:native.latitude,longitude:native.longitude,accuracy:Number(native.accuracy)||0}};""")
# Native package uses only the original platform album API.
js,n=re.subn(r"// WEB_IMAGE_SAVE_BEGIN[^\n]*\n[\s\S]*?// WEB_IMAGE_SAVE_END\n","",js,count=1)
assert n==1
replace('if(!window.xhs)$("achievementHint").textContent=imageSaveHint();','')
replace('if(!window.xhs)$("posterHint").textContent=imageSaveHint();','')
for pattern in [r"if\(!window\.xhs&&navigator\.geolocation\)\{.*?return;\}",r"if\(!window\.xhs\)\{return saveWebImage\(data,button,hint\);\}",r"if\(v&&!window\.xhs\)\{window\.open\(.*?return;\}",r"if\(!window\.xhs\)\{e\.preventDefault\(\);window\.open\(.*?return;\}"]:
    js,n=re.subn(pattern,"",js,count=1)
    assert n==1,pattern
poly="""if(!Array.prototype.at)Object.defineProperty(Array.prototype,'at',{configurable:true,writable:true,value:function(i){i=Math.trunc(Number(i)||0);return this[i<0?this.length+i:i];}});if(!Object.fromEntries)Object.fromEntries=function(entries){var out={};for(var entry of entries)out[entry[0]]=entry[1];return out;};\n"""
js=poly+js
m=re.search(r'const v604Assets=(\{[^\n]+\});',js)
assert m
assets=json.loads(m.group(1))
assert len(assets)==60 and sum('/bw-' in k for k in assets)==30
js=js[:m.start()]+js[m.end():]
replace('function v604Sprite(id){let u=LOCAL_ART[DEX[id]];return v604Assets[has({id})?u:u.replace("/images/","/images/bw-")]||"";}','function v604Sprite(id){let u=LOCAL_ART[DEX[id]];return u?(has({id})?u:u.replace("/images/","/images/bw-")):"";}')
assert not re.search(r'localStorage|sessionStorage|indexedDB|window\.open\(|navigator\.geolocation|\.download\s*=',js)
assert not re.search(r'<(?:script|img|link)\b[^>]*(?:src|href)=["\x27]https?://',html,re.I)
root=Path("dist")
if root.exists(): shutil.rmtree(root)
m=re.search(r'src="data:image/webp;base64,([^"]+)"',html)
assert m
banner=base64.b64decode(m.group(1),validate=True)
html=html[:m.start()]+'src="./banner.webp"'+html[m.end():]
for name in ("xhs-pixel","xhs-silhouette"):
    d=root/name
    d.mkdir(parents=True)
    (d/"images").mkdir()
    (d/"banner.webp").write_bytes(banner)
    (d/"index.html").write_text(html,encoding="utf-8")
    (d/"app.raw.js").write_text(js,encoding="utf-8")
    shutil.copyfile("game-theme.css",d/"game-theme.css")
    fonts=d/"assets/fonts"
    fonts.mkdir(parents=True)
    for font_file in Path("assets/fonts").iterdir():
        if font_file.suffix.lower() in (".woff", ".woff2"):
            shutil.copyfile(font_file,fonts/font_file.name)
        elif font_file.suffix.lower() in (".txt", ".md"):
            content=font_file.read_bytes().decode("utf-8")
            assert "*/" not in content, font_file.name
            with (d/"game-theme.css").open("a",encoding="utf-8") as css:
                css.write("\n/* "+font_file.name+"\n"+content+"\n*/\n")
        else:
            raise ValueError("Unsupported font resource: "+font_file.name)
    if name=="xhs-pixel":
        for path,data in assets.items():
            assert path.startswith("./images/") and data.startswith("data:image/png;base64,")
            raw=base64.b64decode(data.split(",",1)[1],validate=True)
            assert raw.startswith(b"\x89PNG\r\n\x1a\n")
            (d/path[2:]).write_bytes(raw)
    else:
        # No original coloured/detailed sprites in this variant. Actual flat silhouettes,
        # including poster/achievement art; preserve pixel alpha and state indication.
        for path,data in assets.items():
            if "/bw-" not in path: continue
            raw=base64.b64decode(data.split(",",1)[1],validate=True)
            im=Image.open(BytesIO(raw)).convert("RGBA")
            alpha=im.getchannel("A")
            assert alpha.getextrema()[0]==0 and alpha.getextrema()[1]>0, path
            for filename,colour in [(path[2:],(76,70,80)),(path[2:].replace("/bw-","/"),(40,99,71))]:
                flat=Image.new("RGBA",im.size,colour+(255,))
                flat.putalpha(alpha)
                flat.save(d/filename,optimize=True)
    assert len(list((d/"images").glob("*.png")))==60
    print(name, "60 local state images, local font/theme/banner, native storage/location")

# Xiaohongshu deployment allowlist (app.raw.js is replaced by app.js in CI).
allowed=set("jpg css gif svg png js jpeg json html woff2 webp woff".split())
for file in root.rglob("*"):
    if file.is_file():
        assert file.suffix.lower().lstrip(".") in allowed, str(file)

for package in root.iterdir():
    assert sorted(str(p.relative_to(package)) for p in package.rglob("*.html"))==["index.html"], package
