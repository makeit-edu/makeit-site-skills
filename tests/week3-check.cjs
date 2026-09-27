/* Uses an existing Playwright/Chrome installation; installs nothing. */
const assert = require('node:assert/strict');
const {chromium} = require('playwright');
const path = require('node:path');
(async () => {
  const [output, url = 'http://127.0.0.1:8794/week3/'] = process.argv.slice(2);
  assert(output, '캡처 저장 폴더가 필요합니다');
  const browser = await chromium.launch({channel:'chrome'});
  try {
    const context = await browser.newContext({permissions:['clipboard-read','clipboard-write']});
    const page = await context.newPage();
    const errors = [];
    page.on('pageerror', e => errors.push(e.message));
    assert.equal((await page.goto(url, {waitUntil:'networkidle'})).status(), 200);
    assert.equal(await page.locator('.step').count(), 8);
    const prompts = new Set();
    for (const choice of ['reading','mobile','speed']) {
      await page.locator(`[name="upgrade"][value="${choice}"]`).check();
      prompts.add(await page.locator('#change-prompt').textContent());
      await page.locator('[data-copy="change-prompt"]').click();
      assert.equal(await page.evaluate(()=>navigator.clipboard.readText()),(await page.locator('#change-prompt').textContent()).trim());
    }
    assert.equal(prompts.size,3,'선택별로 서로 다른 요청문');
    assert.equal(await page.locator('#speed-first').isVisible(),true);
    assert.equal(await page.locator('#speed-guide').getAttribute('open'),'');
    await page.locator('[name="upgrade"][value="reading"]').check();
    assert.equal(await page.locator('#speed-first').isVisible(),false);
    await page.locator('#step-5 summary').click();
    for (const scheme of ['light', 'dark']) {
      await page.emulateMedia({colorScheme:scheme});
      for (const width of [1440, 390, 320]) {
        await page.setViewportSize({width, height:1000});
        await page.evaluate(() => scrollTo(0,0));
        assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);
        await page.screenshot({path:path.join(output, `week3-${scheme}-${width}.png`)});
        for (const id of ['step-3','step-4','step-5','step-6','step-8']) {
          await page.locator('#'+id).scrollIntoViewIfNeeded();
          await page.screenshot({path:path.join(output, `week3-${scheme}-${width}-${id}.png`)});
        }
        const images = page.locator('img');
        for (const img of await images.all()) {
          await img.scrollIntoViewIfNeeded();
          await img.evaluate(node => node.decode());
        }
        assert.equal(await images.evaluateAll(nodes => nodes.filter(n=>!n.complete || n.naturalWidth===0).length),0);
      }
    }
    for (const id of ['install-prompt','change-prompt','check-prompt','zip-prompt','speed-prompt']) {
      await page.locator(`[data-copy="${id}"]`).click();
      assert.equal(await page.evaluate(()=>navigator.clipboard.readText()),(await page.locator('#'+id).textContent()).trim());
    }
    await page.locator('#build-prompt').click();
    assert.equal(await page.locator('#personal-result').isVisible(),false);
    await page.locator('#idea').fill('카드 제목을 더 크게 해줘. <script>오류</script>');
    await page.locator('#build-prompt').click();
    assert.equal(await page.locator('#personal-result').isVisible(),true);
    assert.equal(await page.locator('#own-prompt script').count(),0);
    await page.locator('[data-copy="own-prompt"]').click();
    assert((await page.evaluate(()=>navigator.clipboard.readText())).includes('카드 제목을 더 크게'));
    await page.evaluate(()=>Object.defineProperty(navigator,'clipboard',{value:{writeText:()=>Promise.reject(new Error('차단'))},configurable:true}));
    await page.locator('[data-copy="change-prompt"]').click();
    await page.getByRole('status').filter({hasText:'직접 복사'}).waitFor();
    assert((await page.evaluate(()=>getSelection().toString())).includes('메킷 사이트 메이커'));
    const paths = await page.locator('a[href],link[href],script[src],img[src]').evaluateAll(nodes=>nodes.map(n=>n.getAttribute('href')||n.getAttribute('src')).filter(s=>s&&!s.startsWith('#')&&!s.startsWith('https:')));
    for (const item of new Set(paths)) assert.equal((await page.request.get(new URL(item,url).href)).status(),200,item);
    assert.equal(errors.length,0);
    console.log('3주차 새 페이지: 8단계, 1440·390·320px, 밝은·어두운 화면, 이미지, 문장 복사·실패 대안, 개인 요청, 링크, JS 오류 검사 통과');
  } finally { await browser.close(); }
})().catch(e=>{console.error(e.message);process.exitCode=1});
