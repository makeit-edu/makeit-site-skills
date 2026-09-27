#!/usr/bin/env python3
"""Local, read-only checks and explicit-manifest ZIP packaging. No network calls."""
import argparse
import hashlib
import io
import json
import re
import shutil
import subprocess
import sys
import zipfile
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath

MAX_FILE = 8 * 1024 * 1024
MAX_TOTAL = 40 * 1024 * 1024
ALLOWED = {".php", ".css", ".js", ".json", ".html", ".txt", ".md", ".svg",
           ".png", ".jpg", ".jpeg", ".webp", ".gif", ".woff2", ".po", ".mo"}
SENSITIVE = re.compile(
    rb"(?:sk-(?:proj-)?[A-Za-z0-9_-]{20,}|gh[pousr]_[A-Za-z0-9]{25,}"
    rb"|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----)"
)

class CheckError(ValueError):
    pass

def safe_file(root, name):
    if not isinstance(name, str) or "\\" in name or ":" in name:
        raise CheckError("잘못된 상대 파일 경로")
    part = PurePosixPath(name)
    if part.is_absolute() or not part.parts or any(p in {".", ".."} or p.startswith(".") for p in name.split("/")):
        raise CheckError("숨김 파일 또는 경로 탈출은 허용하지 않음")
    current = root
    for segment in part.parts:
        current = current / segment
        if current.is_symlink():
            raise CheckError("심볼릭 링크는 허용하지 않음")
    if not current.is_file() or not current.resolve().is_relative_to(root.resolve()):
        raise CheckError("폴더 안의 일반 파일만 허용")
    return current

class PageFacts(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.titles, self.canonicals, self.robots = [], [], []
        self.headings, self.images, self.links, self.jsonld = [], [], [], []
        self.title = None
        self.heading = None
        self.ld = None
        self.base_count = 0

    def handle_starttag(self, tag, pairs):
        attrs = dict(pairs)
        if tag == "title":
            self.title = []
        if tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            self.heading = [tag, []]
        if tag == "base":
            self.base_count += 1
        if tag == "link" and "canonical" in (attrs.get("rel") or "").lower().split():
            self.canonicals.append(attrs.get("href", ""))
        if tag == "meta" and (attrs.get("name") or "").lower() in {"robots", "googlebot"}:
            self.robots.append({"name": attrs.get("name"), "content": attrs.get("content", "")})
        if tag == "img":
            self.images.append({"has_alt": "alt" in attrs, "empty_alt": attrs.get("alt") == "",
                                "has_size": bool(attrs.get("width") and attrs.get("height"))})
        if tag == "a":
            self.links.append(attrs.get("href"))
        if tag == "script" and (attrs.get("type") or "").lower().split(";")[0].strip() == "application/ld+json":
            self.ld = []

    def handle_data(self, data):
        if self.title is not None:
            self.title.append(data)
        if self.heading is not None:
            self.heading[1].append(data)
        if self.ld is not None:
            self.ld.append(data)

    def handle_endtag(self, tag):
        if tag == "title" and self.title is not None:
            self.titles.append("".join(self.title).strip())
            self.title = None
        if self.heading is not None and tag == self.heading[0]:
            self.headings.append({"level": tag, "text": "".join(self.heading[1]).strip()})
            self.heading = None
        if tag == "script" and self.ld is not None:
            try:
                value = json.loads("".join(self.ld))
                valid = isinstance(value, (dict, list))
                self.jsonld.append({"json_valid": True, "object_or_array": valid})
            except (ValueError, RecursionError):
                self.jsonld.append({"json_valid": False, "object_or_array": False})
            self.ld = None

def inspect_html(path):
    path = Path(path)
    if path.stat().st_size > MAX_FILE:
        raise CheckError("HTML 파일이 검사 크기 제한을 초과")
    page = PageFacts()
    page.feed(path.read_text(encoding="utf-8-sig"))
    page.close()
    notes = []
    if len(page.titles) != 1 or not page.titles[0]:
        notes.append("title 누락·빈 값·중복 여부 확인")
    if len(page.canonicals) > 1:
        notes.append("canonical 중복 여부 확인")
    if any(not item["json_valid"] or not item["object_or_array"] for item in page.jsonld):
        notes.append("JSON-LD 문법 또는 최상위 자료형 확인")
    if page.ld is not None:
        notes.append("닫히지 않은 JSON-LD script 확인")
    missing_alt = sum(not i["has_alt"] for i in page.images)
    if missing_alt:
        notes.append("alt 속성이 없는 이미지의 용도 확인")
    return {
        "status": "관찰 완료", "scope": "저장 HTML만 검사",
        "title_count": len(page.titles), "canonical_count": len(page.canonicals),
        "robots_noindex_observed": any("noindex" in str(r["content"]).lower() for r in page.robots),
        "h1_count": sum(h["level"] == "h1" for h in page.headings),
        "link_count": len(page.links),
        "non_navigation_links": sum(not href or href.strip().lower().startswith(("javascript:", "#")) for href in page.links),
        "image_count": len(page.images), "missing_alt_count": missing_alt,
        "empty_alt_count": sum(i["empty_alt"] for i in page.images),
        "without_explicit_size_count": sum(not i["has_size"] for i in page.images),
        "jsonld": page.jsonld, "base_element_count": page.base_count,
        "review": notes,
        "unverified": ["HTTP 응답·헤더", "robots.txt", "링크 목적지", "브라우저 렌더링",
                       "Google 구조화 데이터 적격성", "색인·순위·AI 인용", "성능"],
    }

def lint_plugin(root, php=None):
    root = Path(root)
    if not root.is_dir() or root.is_symlink():
        raise CheckError("일반 플러그인 폴더를 지정")
    files = sorted(p for p in root.rglob("*") if p.suffix.lower() == ".php")
    if not files:
        return {"status": "미검증", "reason": "PHP 파일 없음", "files": []}, 2
    binary = php or shutil.which("php")
    if not binary:
        return {"status": "미검증", "reason": "PHP 실행 환경 없음", "files": []}, 2
    rows = []
    for file in files:
        safe_file(root, file.relative_to(root).as_posix())
        try:
            result = subprocess.run([binary, "-n", "-l", str(file.resolve())],
                                    capture_output=True, timeout=20, check=False)
        except (OSError, subprocess.TimeoutExpired):
            return {"status": "미검증", "reason": "PHP 실행 실패 또는 시간 초과", "files": rows}, 2
        rows.append({"file": file.relative_to(root).as_posix(), "passed": result.returncode == 0})
    passed = all(r["passed"] for r in rows)
    return {"status": "구문 통과" if passed else "구문 실패", "files": rows,
            "unverified": ["WordPress 활성화", "기능·보안·화면", "다른 PHP 버전 호환성"]}, 0 if passed else 1

def package_plugin(root, manifest, output):
    root, output = Path(root), Path(output)
    if not root.is_dir() or root.is_symlink():
        raise CheckError("일반 플러그인 폴더를 지정")
    if output.exists() or output.is_symlink():
        raise CheckError("기존 출력 파일을 덮어쓸 수 없음")
    if output.resolve().is_relative_to(root.resolve()):
        raise CheckError("ZIP은 플러그인 폴더 밖에 저장")
    spec = json.loads(Path(manifest).read_text(encoding="utf-8"))
    if not isinstance(spec, dict):
        raise CheckError("manifest는 slug와 files를 가진 객체여야 함")
    slug, names = spec.get("slug"), spec.get("files")
    if not isinstance(slug, str) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug):
        raise CheckError("플러그인 slug는 영문 소문자·숫자·하이픈")
    if not isinstance(names, list) or not names or not all(isinstance(n, str) for n in names):
        raise CheckError("files에 상대 파일 경로 목록 필요")
    if len({n.casefold() for n in names}) != len(names):
        raise CheckError("중복 파일 경로")
    entries, total, main_found = [], 0, False
    for name in sorted(names):
        file = safe_file(root, name)
        if (file.suffix.lower() not in ALLOWED and file.name.upper() != "LICENSE") or any(p.lower() in {"node_modules", "vendor", "backups"} for p in file.relative_to(root).parts):
            raise CheckError("배포 허용 목록 밖의 파일")
        if re.search(r"(?:^|/)(?:wp-config|credentials|secrets|키설정|설정)\b", name, re.I):
            raise CheckError("설정·자격증명 파일은 포장 금지")
        if file.stat().st_size > MAX_FILE:
            raise CheckError("파일 크기 제한 초과")
        data = file.read_bytes()
        total += len(data)
        if total > MAX_TOTAL:
            raise CheckError("전체 크기 제한 초과")
        if SENSITIVE.search(data):
            raise CheckError("비밀값으로 의심되는 내용 발견: 포장 중단")
        if len(PurePosixPath(name).parts) == 1 and file.suffix == ".php":
            main_found |= bool(re.search(rb"(?mi)^\s*\*\s*Plugin Name:\s*\S", data[:8192]))
        entries.append((name, data))
    if not main_found:
        raise CheckError("최상위 PHP 파일에 Plugin Name 헤더 필요")
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zipped:
        for name, data in entries:
            item = zipfile.ZipInfo(slug + "/" + name, (2026, 1, 1, 0, 0, 0))
            item.compress_type = zipfile.ZIP_DEFLATED
            item.external_attr = 0o100644 << 16
            zipped.writestr(item, data)
    payload = archive.getvalue()
    with output.open("xb") as stream:
        stream.write(payload)
    return {"status": "ZIP 생성", "files": [name for name, _ in entries],
            "sha256": hashlib.sha256(payload).hexdigest(),
            "unverified": ["비밀값 전체 탐지", "WordPress 작동", "배포 권리·라이선스"]}

def main():
    parser = argparse.ArgumentParser(description="메킷 로컬 검사: 네트워크 접근·사이트 수정 없음")
    commands = parser.add_subparsers(dest="command", required=True)
    html = commands.add_parser("html", help="저장 HTML 관찰")
    html.add_argument("file")
    lint = commands.add_parser("lint", help="PHP 구문 검사")
    lint.add_argument("folder")
    pack = commands.add_parser("package", help="명시한 파일만 새 ZIP으로 포장")
    pack.add_argument("folder")
    pack.add_argument("manifest")
    pack.add_argument("output")
    args = parser.parse_args()
    code = 0
    try:
        if args.command == "html":
            result = inspect_html(args.file)
        elif args.command == "lint":
            result, code = lint_plugin(args.folder)
        else:
            result = package_plugin(args.folder, args.manifest, args.output)
    except (OSError, ValueError, TypeError, zipfile.BadZipFile) as error:
        message = str(error) if isinstance(error, CheckError) else "입력 파일·형식·접근 권한을 확인하세요"
        result, code = {"status": "실행 중단", "reason": message}, 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return code

if __name__ == "__main__":
    sys.exit(main())
