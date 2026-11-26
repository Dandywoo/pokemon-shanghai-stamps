from pathlib import Path
import re, json, base64, shutil

source=Path("silhouette/index.html").read_text(encoding="utf-8")
assert 'window.__dexVersion="7.1.7"' in source, "Wrong version"
source=source.replace("7.1.7","7.1.8")
# No colored tile backgrounds when collection state changes; the check button is retained.
source=source.replace("</style>", ".dex-tile.pixel-dex-tile.is-done{background:#e8eef0;border-color:#ccdadd;box-shadow:none}.dex-tile.pixel-dex-tile.is-done.is-target{border-color:#cbac65}.dex-tile.pixel-dex-tile.is-done .dex-id{font-weight:inherit}</style>",1)
scripts=re.findall(r'<script\b[^>]*>([\s\S]*?)</script>',source,re.I)
assert len(scripts)==1
js=scripts[0]
html=re.sub(r'<script\b[^>]*>[\s\S]*?</script>', '<script src="./app.js"></script>',source,count=1,flags=re.I)
def replace(a,b):
    global js
    assert js.count(a)==1, (a[:100],js.count(a))
    js=js.replace(a,b,1)
def region(a,b,new):
    global js
    i=js.index(a); j=js.index(b,i+len(a))
    js=js[:i]+new+js[j:]
# Keep native storage key and original data; extend the validated schema.
replace('draft: a.draft && typeof a.draft === "object" ? a.draft : {},', '''draft: a.draft && typeof a.draft === "object" ? a.draft : {}, manualRoute: a.manualRoute && typeof a.manualRoute === "object" ? a.manualRoute : {}, achievementGoals: Array.isArray(a.achievementGoals) ? a.achievementGoals.filter(Number.isInteger).slice(0,100) : [],''')
# SDK absence or unknown version never falls back to browser cache.
a=js.index('if(!x||!x.miniTool){try{const raw=localStorage')
b=js.index('mini = x && x.miniTool;',a)
js=js[:a]+'''if(!x||!x.miniTool){storageStatus('本次无法保存进度，请使用文本备份。');return;}\n        '''+js[b:]
replace("JSON.parse(localStorage.getItem('sh-pokemon-stamps-v7-ach')||'[]')","(state.achievementGoals||[])")
replace("localStorage.setItem('sh-pokemon-stamps-v7-ach',JSON.stringify([...window.__v7Goals]))","state.achievementGoals=[...window.__v7Goals];save()")
a="JSON.parse(localStorage.getItem('sh-pokemon-stamps-manual-route-v1')||'null')"
assert js.count(a)==2
js=js.replace(a,"(state.manualRoute||null)")
replace("localStorage.setItem('sh-pokemon-stamps-manual-route-v1',JSON.stringify({active:window.manualMode,ids:[...window.manualVenues],goal:window.manualGoal,goalMode:window.manualGoalMode}))","const draft={active:window.manualMode,ids:[...window.manualVenues],goal:window.manualGoal,goalMode:window.manualGoalMode};if(JSON.stringify(state.manualRoute)!==JSON.stringify(draft)){state.manualRoute=draft;save()}")
# Remove browser-only actions from the container package.
for pattern in [r"if\(!window\.xhs&&navigator\.geolocation\)\{.*?return;\}",r"if\(!window\.xhs\)\{const a=document\.createElement\('a'\);a\.href=data;.*?return;\}",r"if\(v&&!window\.xhs\)\{window\.open\(.*?return;\}",r"if\(!window\.xhs\)\{e\.preventDefault\(\);window\.open\(.*?return;\}"]:
    js,n=re.subn(pattern,"",js,count=1)
    assert n==1,pattern
# API polyfills for the Android minimum baseline (compiler handles syntax only).
poly="""if(!Array.prototype.at)Object.defineProperty(Array.prototype,'at',{configurable:true,writable:true,value:function(i){i=Math.trunc(Number(i)||0);return this[i<0?this.length+i:i];}});if(!Object.fromEntries)Object.fromEntries=function(entries){var out={};for(var entry of entries)out[entry[0]]=entry[1];return out;};\n"""
js=poly+js
# Extract all 60 existing sprites to local assets without redrawing or changing them.
m=re.search(r'const v604Assets=(\{[^\n]+\});',js)
assert m
assets=json.loads(m.group(1))
assert len(assets)==60 and sum('/bw-' in k for k in assets)==30
js=js[:m.start()]+js[m.end():]
replace('function v604Sprite(id){let u=LOCAL_ART[DEX[id]];return v604Assets[has({id})?u:u.replace("/images/","/images/bw-")]||"";}','function v604Sprite(id){let u=LOCAL_ART[DEX[id]];return u?u.replace("/images/","/images/bw-"):"";}')
# Static package contains no outbound resource URLs. Official URLs remain plain text for users.
assert not re.search(r'localStorage|sessionStorage|indexedDB|window\.open\(|navigator\.geolocation|\.download\s*=',js)
assert not re.search(r'<(?:script|img|link)\b[^>]*(?:src|href)=["\x27]https?://',html,re.I)
root=Path("dist")
if root.exists(): shutil.rmtree(root)
pixel=root/"xhs-pixel"; number=root/"xhs-number"
for d in [pixel,number]: d.mkdir(parents=True)
for path,data in assets.items():
    if "/bw-" not in path: continue
    assert path.startswith("./images/") and data.startswith("data:image/png;base64,")
    target=pixel/path[2:];target.parent.mkdir(exist_ok=True)
    raw=base64.b64decode(data.split(",",1)[1],validate=True)
    assert raw.startswith(b"\x89PNG\r\n\x1a\n")
    target.write_bytes(raw)
# Keep theme banner local instead of embedding a large image.
m=re.search(r'src="data:image/webp;base64,([^"]+)"',html)
if m:
    (pixel/"banner.webp").write_bytes(base64.b64decode(m.group(1),validate=True))
    pixel_html=html[:m.start()]+'src="./banner.webp"'+html[m.end():]
else: pixel_html=html
(pixel/"index.html").write_text(pixel_html,encoding="utf-8")
(pixel/"app.raw.js").write_text(js,encoding="utf-8")
# Number-only variant: no monster images, including in progress/achievement cards.
num=js
a=num.index('function v604Sprite(id)');b=num.index('const LOCAL_ART',a)
num=num[:a]+'''function v604Sprite(id){const c=document.createElement('canvas');c.width=c.height=96;const ctx=c.getContext('2d');ctx.fillStyle='#42505a';ctx.font='bold 20px sans-serif';ctx.textAlign='center';ctx.textBaseline='middle';ctx.fillText(dexNo(id),48,48);return c.toDataURL('image/png');}\n      '''+num[b:]
num=re.sub(r'const LOCAL_ART\s*=\s*\{[^\n]*\};','const LOCAL_ART = {};',num,count=1)
# The skyline banner has no monster character but number-only variant omits imagery entirely.
nh=re.sub(r'<img\b[^>]*class="pixel-banner"[^>]*>', '', html,count=1)
(number/"index.html").write_text(nh,encoding="utf-8")
(number/"app.raw.js").write_text(num,encoding="utf-8")
assert len(list((pixel/"images").glob("*.png")))==30
assert all(p.name.startswith("bw-") for p in (pixel/"images").glob("*.png"))
print("Pixel:",len(list(pixel.rglob("*"))),"entries, 30 monochrome sprites only; number-only: no monster assets")
