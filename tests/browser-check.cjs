/* Requires an existing Playwright installation and Chromium; installs nothing. */
const assert = require('node:assert/strict');
const { chromium } = require('playwright');
(async () => {
  const [url, selector, screenshotPath] = process.argv.slice(2);
  assert(url && selector, 'URL과 카드 영역 선택자가 필요합니다');
  const target = new URL(url);
  assert(['127.0.0.1', 'localhost'].includes(target.hostname), '로컬 시험 URL만 허용');
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  try {
    const page = await browser.newPage();
    const errors = [];
    page.on('pageerror', e => errors.push(e.message));
    await page.route('**/*', route => {
      const u = new URL(route.request().url());
      return u.origin === target.origin ? route.continue() : route.abort();
    });
    const response = await page.goto(url, { waitUntil: 'networkidle' });
    assert.equal(response.status(), 200);
    const cards = page.locator(selector);
    assert.equal(await cards.count(), 1, '카드 영역은 하나');
    const links = cards.locator('a');
    assert.equal(await links.count(), 5, '공개된 관련 글 5개');
    const hrefs = await links.evaluateAll(nodes => nodes.map(n => n.href));
    assert.equal(new Set(hrefs).size, 5, '중복 링크 없음');
    assert(!hrefs.some(href => /[?&]p=(5|11|12|13)(?:&|$)/.test(href)), '현재·임시·비공개·비밀번호 글 제외');
    for (const href of hrefs) {
      assert.equal((await page.request.get(href)).status(), 200, '목적지 응답');
    }
    const snapshots = [];
    for (const width of [1440, 390]) {
      await page.setViewportSize({width, height:1000});
      await cards.scrollIntoViewIfNeeded();
      const geometry = await links.evaluateAll(nodes => nodes.map(n => {
        const b=n.getBoundingClientRect(); return {x:b.x,y:b.y,width:b.width};
      }));
      assert.equal(geometry.length,5);
      if (width===1440) {
        assert(Math.abs(geometry[0].y-geometry[2].y)<2, '데스크톱 3열');
      } else {
        assert(geometry[1].y>geometry[0].y+20, '모바일 1열');
        assert(Math.abs(geometry[0].x-geometry[1].x)<2);
      }
      const overflow = await page.evaluate(() => document.documentElement.scrollWidth>innerWidth);
      assert.equal(overflow,false,'가로 넘침 없음');
      const broken = await cards.locator('img').evaluateAll(nodes => nodes.filter(n=>!n.complete||n.naturalWidth===0).length);
      assert.equal(broken,0,'이미지 로드');
      snapshots.push({width, links:geometry.length, overflow, brokenImages:broken});
      if (screenshotPath) {
        await cards.screenshot({path:screenshotPath.replace('.png', '-'+width+'.png')});
      }
    }
    await links.first().focus();
    assert.equal(await links.first().evaluate(n=>document.activeElement===n), true);
    assert.equal(errors.length,0,'브라우저 JS 오류 없음');
    console.log(JSON.stringify({결과:'통과',화면:snapshots,자바스크립트오류:errors.length},null,2));
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error.message); process.exitCode=1; });
