(() => {
  const notice = document.getElementById('notice');
  let timer;
  function announce(message) {
    notice.textContent = message;
    notice.classList.add('visible');
    clearTimeout(timer);
    timer = setTimeout(() => notice.classList.remove('visible'), 3500);
  }
  document.querySelectorAll('[data-copy]').forEach(button => {
    button.addEventListener('click', async () => {
      const target = document.getElementById(button.dataset.copy);
      try {
        await navigator.clipboard.writeText(target.textContent.trim());
        announce('복사했어요. 코덱스 채팅창에 붙여넣으세요.');
      } catch {
        const selection = window.getSelection();
        const range = document.createRange();
        range.selectNodeContents(target);
        selection.removeAllRanges();
        selection.addRange(range);
        announce('문장을 선택했어요. 직접 복사해 주세요.');
      }
    });
  });
  document.getElementById('build-prompt').addEventListener('click', () => {
    const idea = document.getElementById('idea');
    if (!idea.value.trim()) {
      announce('바꾸고 싶은 것 한 가지를 먼저 적어주세요.');
      idea.focus();
      return;
    }
    document.getElementById('own-prompt').textContent = '메킷 사이트 메이커를 사용해서 내 작업본을 수정해줘. ' + idea.value.trim() + ' 원본과 다른 기능은 유지하고, 바꾼 뒤 화면과 작동을 다시 확인해줘. 못 확인한 것은 따로 알려줘.';
    document.getElementById('personal-result').hidden = false;
    announce('요청문을 만들었어요. 아래 복사 버튼을 누르세요.');
  });
})();
