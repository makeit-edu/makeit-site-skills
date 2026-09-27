(() => {
  const notice = document.getElementById('notice');
  let timer;
  const prompt = document.getElementById('change-prompt');
  const readingPrompt = prompt.textContent;
  const boundary = ' 원본과 기존 글·라이선스·광고·초기화 기능은 유지하고 작업본만 다뤄줘. 새 사이트나 새 글, 별도 플러그인은 만들지 마. 테마나 서버 변경이 필요하면 먼저 설명해줘.';
  const choices = {
    reading: readingPrompt,
    mobile: '메킷 사이트 메이커로 내 메킷애센을 업그레이드해줘. 휴대폰에서 기존 목차·관련 글·이미지가 겹치거나 화면 밖으로 넘치는지 먼저 확인해줘. 실제로 문제가 있는 항목과 수정안을 보여주면 내가 하나 고를게. 아직 수정하지 말고 현재 화면을 남겨줘.' + boundary,
    speed: '메킷 사이트 메이커로 내 메킷애센의 속도 개선을 준비해줘. 먼저 같은 글의 PageSpeed 결과와 측정 조건을 확인하고, 플러그인이 원인인 항목을 찾아 제안해줘. 측정 자료가 없으면 무엇을 보내야 하는지 알려줘. 아직 수정하지 마.' + boundary
  };
  document.querySelectorAll('[name="upgrade"]').forEach(input => input.addEventListener('change', () => {
    prompt.textContent = choices[input.value];
    document.getElementById('speed-first').hidden = input.value !== 'speed';
    if (input.value === 'speed') document.getElementById('speed-guide').open = true;
    announce('선택한 항목의 요청 문장으로 바꿨어요.');
  }));
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
    document.getElementById('own-prompt').textContent = '메킷 사이트 메이커로 내 메킷애센 작업본을 업그레이드해줘. ' + idea.value.trim() + boundary + ' 변경 전후 화면과 작동을 확인하고, 속도 관련 변경은 같은 조건에서 측정해줘. 못 확인한 것은 따로 알려줘.';
    document.getElementById('personal-result').hidden = false;
    announce('요청문을 만들었어요. 아래 복사 버튼을 누르세요.');
  });
})();
