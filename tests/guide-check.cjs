const assert=require('node:assert/strict');
const {chromium}=require('playwright');
(async()=>{
 const browser=await chromium.launch({channel:'chrome'});
 try {
  const context=await browser.newContext({permissions:['clipboard-read','clipboard-write']});
  const page=await context.newPage(); const errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  await page.goto(process.argv[3]||'http://127.0.0.1:8794/',{waitUntil:'networkidle'});
  for(const width of [1440,390]){
   await page.setViewportSize({width,height:1000});
   assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
   assert.equal(await page.locator('img').evaluateAll(ns=>ns.filter(n=>!n.complete||n.naturalWidth===0).length),0);
   await page.screenshot({path:process.argv[2]+'/guide-'+width+'.png',fullPage:true});
  }
  await page.locator('[data-copy="prompt-first"]').click();
  assert((await page.evaluate(()=>navigator.clipboard.readText())).includes('메킷 사이트 메이커'));
  await page.locator('#idea').fill('카드의 글자를 조금 더 크게 바꿔줘.');
  await page.locator('#build-prompt').click();
  assert((await page.locator('#own-prompt').textContent()).includes('글자를 조금 더 크게'));
  await page.locator('[data-step="1"]').check();
  await page.locator('[data-step="2"]').check();
  assert.equal(await page.locator('#progress-text').textContent(),'2 / 6 확인');
  await page.reload();
  assert.equal(await page.locator('#progress-text').textContent(),'2 / 6 확인');
  const anchors=await page.locator('a[href^="#"]').evaluateAll(ns=>ns.map(n=>n.getAttribute('href')));
  for(const anchor of anchors) assert.equal(await page.locator(anchor).count(),1);
  assert.equal(errors.length,0);
  console.log('가이드: 데스크톱·모바일 넘침 없음, 이미지 로드·복사·개인 요청·진행 저장·앵커·JS 검사 통과');
 }finally{await browser.close()}
})().catch(e=>{console.error(e.message);process.exitCode=1});
