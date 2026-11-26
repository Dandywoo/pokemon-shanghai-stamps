const {chromium}=require('playwright');
const assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({channel:'chrome',headless:true,args:['--no-sandbox']});
 for(const variant of ['xhs-pixel','xhs-silhouette']){
  const page=await browser.newPage({viewport:{width:390,height:844},isMobile:true});
  let snapshot=null,errors=[],requests=[];
  await page.exposeFunction('testRead',()=>snapshot);
  await page.exposeFunction('testWrite',v=>{snapshot=v;return {errMsg:'setStorage:ok'}});
  await page.addInitScript(()=>{
   window.xhs={launchOptions:{miniToolEnv:{buildVersion:9500000}},miniTool:{
    getStorage:async()=>({errMsg:'getStorage:ok',data:await window.testRead()}),
    setStorage:async({data})=>window.testWrite(data),
    getLocation:async()=>({errMsg:'getLocation:ok',latitude:31.220,longitude:121.420,accuracy:20})
   }};
  });
  page.on('pageerror',e=>errors.push(e.message));
  page.on('requestfailed',r=>requests.push(r.url()));
  await page.goto('http://127.0.0.1:8765/dist/'+variant+'/index.html');
  await page.waitForFunction(()=>window.__dexVersion==='7.2.2'&&document.querySelector('#startupGate')?.hidden);
  assert.equal(await page.locator('header h1').innerText(),'上海盛典图鉴');
  assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  await page.evaluate(()=>document.fonts.ready);
  assert.ok(await page.evaluate(()=>document.fonts.check('16px "Fusion Pixel UI"','捕捉')));
  await page.locator('#tabList').click();
  const tile=page.locator('[data-pocket]').first();
  const img=page.locator('.dex-tile [data-dex-art]').first();
  const before=await img.getAttribute('src');
  assert.match(before,/bw-/);
  await img.scrollIntoViewIfNeeded();
  await page.waitForFunction(()=>document.querySelector('.dex-tile [data-dex-art]')?.naturalWidth>0);
  await tile.click();
  await page.waitForFunction(()=>document.querySelector('.dex-tile [data-dex-art]')?.naturalWidth>0);
  assert.match(await tile.getAttribute('title'),/已捕捉.*放生/);
  assert.ok(!(await img.getAttribute('src')).includes('bw-'));
  await tile.click();assert.equal(await tile.innerText(),'+');
  await tile.click();
  await page.waitForTimeout(300);
  assert.ok(JSON.parse(snapshot).done.length>0);
  await page.reload();
  await page.waitForFunction(()=>window.__dexVersion==='7.2.2'&&document.querySelector('#startupGate')?.hidden);
  await page.locator('#tabList').click();assert.match(await page.locator('[data-pocket]').first().getAttribute('title'),/已捕捉/);
  await page.locator('#tabMap').click();
  await page.locator('#v6MapOrigin').evaluate(e=>e.closest('details').open=true);
  await page.locator('#v6MapGPS').click();
  await page.waitForFunction(()=>document.querySelector('#originSource').value==='gps');
  assert.ok(await page.locator('#gpsMapOrigin option').count()>=2);
  assert.ok(await page.locator('#exploreMap g[data-v6-pin] .game-map-pin').count()>0);
  await page.locator('#v6MapCompute').click();
  await page.waitForFunction(()=>!document.querySelector('#v6MapCompute').disabled);
  assert.match(await page.locator('#v6MapResult').innerText(),/预计新增/);
  assert.deepEqual(errors,[]);assert.deepEqual(requests,[]);
  console.log(variant,'native mock storage/reload/capture/release/location/route OK');
  await page.close();
 }
 await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});
