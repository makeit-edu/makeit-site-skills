(() => {
  const toast = document.querySelector('#toast');
  let timer;
  function notify(message) {
    toast.textContent = message;
    toast.classList.add('visible');
    clearTimeout(timer);
    timer = setTimeout(() => toast.classList.remove('visible'), 2400);
  }
  document.querySelectorAll('[data-copy]').forEach(button => {
    button.addEventListener('click', async () => {
      const target = document.getElementById(button.dataset.copy);
      try {
        await navigator.clipboard.writeText(target.textContent.trim());
        notify('복사했어요. Codex에 붙여넣으세요.');
      } catch {
        const selection = window.getSelection();
        const range = document.createRange();
        range.selectNodeContents(target);
        selection.removeAllRanges(); selection.addRange(range);
        notify('문장을 선택했어요. 직접 복사해 주세요.');
      }
    });
  });
  document.querySelector('#build-prompt').addEventListener('click', () => {
    const idea = document.querySelector('#idea').value.trim();
    if (!idea) { notify('원하는 변화 한 가지를 적어주세요.'); return; }
    const target = document.querySelector('#own-prompt');
    target.textContent = '메킷 사이트 메이커를 사용해 작업본을 수정해줘. ' + idea + ' 다른 기능은 유지하고, 변경 전후를 확인해줘. 못 확인한 것은 따로 알려줘.';
    target.hidden = false;
    document.querySelector('#copy-own').hidden = false;
  });
  const checks = [...document.querySelectorAll('[data-step]')];
  function update() {
    const count = checks.filter(c => c.checked).length;
    document.querySelector('#progress-text').textContent = count + ' / 6 확인';
    document.querySelector('#progress').value = count;
  }
  // Progress stays in this browser only; it is not evidence of technical validation.
  try {
    const saved = JSON.parse(localStorage.getItem('makeit-week3-v1') || '[]');
    if (Array.isArray(saved)) checks.forEach(c => c.checked = saved.includes(c.dataset.step));
  } catch { notify('진행 기록을 불러오지 못했어요. 실습은 계속할 수 있어요.'); }
  checks.forEach(c => c.addEventListener('change', () => {
    update();
    try { localStorage.setItem('makeit-week3-v1', JSON.stringify(checks.filter(x=>x.checked).map(x=>x.dataset.step))); }
    catch { notify('체크 상태는 이 화면에서만 유지됩니다.'); }
  }));
  update();
})();
