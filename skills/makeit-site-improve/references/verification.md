# 검사와 전달
## 검사 층
1. 변경 파일·범위: 원본과 작업본 비교. 요청 밖 변경이 없는지 확인.
2. 구문: PHP·JS 문법. 이것은 WordPress 실행 시험이 아님.
3. 실행: 테스트 WordPress 활성화, 출력·링크·설정 유지·비활성화·재활성화.
4. 화면: 같은 조건의 데스크톱·모바일 전후. 실제 이미지 로드·긴 제목·키보드 확인.
5. 검색: 관련 title/canonical/robots/schema와 실제 링크 비교. 색인·순위는 별도.
6. 복구: 파일 복구와 DB/업로드 복구의 범위를 나눔. 초기화 버튼은 복구가 아님.

## 내장 도구
스크립트 경로를 스킬 설치 위치 기준으로 해석한다.
- `python3 scripts/site_check.py html PAGE.html`: 저장 HTML의 title, canonical, robots, 링크·이미지·JSON-LD 관찰. 렌더링·네트워크·Google 적격성은 미검증.
- `python3 scripts/site_check.py lint PLUGIN_FOLDER`: PHP 파일에 실제 php -l 실행. PHP가 없거나 검사 파일이 없으면 미검증.
- `python3 scripts/site_check.py package PLUGIN_FOLDER MANIFEST.json OUTPUT.zip`: 명시한 상대 파일 경로만 ZIP에 담는다. 기존 ZIP 덮어쓰기·경로 탈출·심볼릭 링크·의심스러운 비밀 파일 거부. 성공은 보안 감사나 활성화 성공을 뜻하지 않음.

MANIFEST.json 예: `{"slug":"my-plugin","files":["my-plugin.php","assets/style.css"]}`
ZIP은 플러그인 폴더 하나를 최상위에 둔다. 스킬 ZIP과 혼동하지 않는다.
오류 출력은 키나 원문을 보여주지 않는다. 도구 종료 코드 0=검사 수행/포장 성공, 1=확인된 실패, 2=입력 또는 환경 문제.
HTML 도구는 발견사항을 보고하며 추천 항목 존재만으로 실패 종료하지 않는다.

## 운영 적용 전
대상 사이트·백업·복구 접근을 확인하고 사용자 권한 범위에서 진행. 작업본 ZIP, 이전 ZIP, DB·업로드 백업은 각각 용도가 다르다.
미확인 사항을 남기고, 라이브 설치 권한이 없으면 설치 지침까지만 전달한다. 검증용 비밀값·DB·로그는 ZIP에 포함하지 않는다.
