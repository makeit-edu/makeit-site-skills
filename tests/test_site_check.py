import importlib.util
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "skills/makeit-site-improve/scripts/site_check.py"
spec = importlib.util.spec_from_file_location("site_check", SCRIPT)
check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check)

class LocalChecks(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.plugin = self.base / "plugin"
        self.plugin.mkdir()
        (self.plugin / "main.php").write_text("<?php\n/**\n * Plugin Name: 연습\n */\n", encoding="utf-8")
        self.manifest = self.base / "manifest.json"
        self.output = self.base / "result.zip"

    def pack(self, files=None, slug="practice"):
        self.manifest.write_text(json.dumps({"slug": slug, "files": files or ["main.php"]}), encoding="utf-8")
        return check.package_plugin(self.plugin, self.manifest, self.output)

    def html(self, text):
        file = self.base / "page.html"
        file.write_text(text, encoding="utf-8")
        return check.inspect_html(file)

    def test_valid_html(self):
        result = self.html('<title>연습</title><h1>제목</h1><a href="/a">글</a><img alt="" width="3" height="2"><script type="application/ld+json">{"@type":"Article"}</script>')
        self.assertEqual(result["review"], [])
        self.assertEqual(result["empty_alt_count"], 1)
        self.assertEqual(result["missing_alt_count"], 0)
        self.assertIn("색인·순위·AI 인용", result["unverified"])

    def test_duplicates(self):
        result = self.html('<title>a</title><title>b</title><link rel="canonical" href="/a"><link rel="Canonical" href="/b">')
        self.assertEqual(result["canonical_count"], 2)
        self.assertEqual(len(result["review"]), 2)

    def test_bad_jsonld(self):
        self.assertFalse(self.html('<script type="application/ld+json">{bad}</script>')["jsonld"][0]["json_valid"])

    def test_scalar_jsonld(self):
        self.assertFalse(self.html('<script type="application/ld+json">42</script>')["jsonld"][0]["object_or_array"])

    def test_unclosed_jsonld(self):
        self.assertIn("닫히지 않은 JSON-LD script 확인", self.html('<script type="application/ld+json">{}')["review"])

    def test_noindex_not_auto_error(self):
        self.assertTrue(self.html('<meta name="robots" content="noindex,follow">')["robots_noindex_observed"])

    def test_missing_alt_and_links(self):
        result = self.html('<img src="a"><a>없음</a><a href="#top">위</a>')
        self.assertEqual(result["missing_alt_count"], 1)
        self.assertEqual(result["non_navigation_links"], 2)

    def test_do_not_leak_page_content(self):
        result = self.html('<title>사적인문구</title><h1>비밀제목</h1>')
        self.assertNotIn("비밀제목", json.dumps(result, ensure_ascii=False))

    def test_package_explicit_files(self):
        (self.plugin / "private.txt").write_text("포함하면 안 됨")
        result = self.pack()
        with zipfile.ZipFile(self.output) as archive:
            self.assertEqual(archive.namelist(), ["practice/main.php"])
            self.assertIsNone(archive.testzip())
        self.assertEqual(len(result["sha256"]), 64)

    def test_reproducible_zip(self):
        first = self.pack()["sha256"]
        self.output = self.base / "second.zip"
        self.assertEqual(first, self.pack()["sha256"])

    def test_no_overwrite(self):
        self.output.write_bytes(b"keep")
        with self.assertRaises(check.CheckError):
            self.pack()
        self.assertEqual(self.output.read_bytes(), b"keep")

    def test_path_escape(self):
        for name in ["../outside.php", "/etc/passwd", "a\\b.php", "a/../main.php", ".env", "C:/main.php", "./main.php"]:
            with self.subTest(name=name), self.assertRaises(check.CheckError):
                self.pack([name])
        self.assertFalse(self.output.exists())

    def test_symlink_file(self):
        (self.plugin / "linked.php").symlink_to(self.plugin / "main.php")
        with self.assertRaises(check.CheckError):
            self.pack(["linked.php"])

    def test_symlink_directory(self):
        (self.plugin / "dir").symlink_to(self.plugin, target_is_directory=True)
        with self.assertRaises(check.CheckError):
            self.pack(["dir/main.php"])

    def test_secret(self):
        (self.plugin / "main.php").write_text("<?php\n/**\n * Plugin Name: x\n */\n// " + "sk-" + "a" * 30)
        with self.assertRaises(check.CheckError):
            self.pack()
        self.assertFalse(self.output.exists())

    def test_config_name(self):
        (self.plugin / "wp-config.php").write_text("<?php")
        with self.assertRaises(check.CheckError):
            self.pack(["main.php", "wp-config.php"])

    def test_bad_slug(self):
        with self.assertRaises(check.CheckError):
            self.pack(slug="../escape")

    def test_missing_header(self):
        (self.plugin / "main.php").write_text("<?php")
        with self.assertRaises(check.CheckError):
            self.pack()

    def test_duplicate_case(self):
        with self.assertRaises(check.CheckError):
            self.pack(["main.php", "MAIN.php"])

    def test_archive_not_inside_plugin(self):
        self.output = self.plugin / "result.zip"
        with self.assertRaises(check.CheckError):
            self.pack()

    def test_missing_php(self):
        with patch.object(check.shutil, "which", return_value=None):
            result, code = check.lint_plugin(self.plugin)
        self.assertEqual(code, 2)
        self.assertEqual(result["status"], "미검증")

    def test_actual_php_syntax(self):
        if not check.shutil.which("php"):
            self.skipTest("PHP 없음")
        self.assertEqual(check.lint_plugin(self.plugin)[1], 0)
        (self.plugin / "main.php").write_text("<?php syntax error")
        self.assertEqual(check.lint_plugin(self.plugin)[1], 1)

    def test_no_php_files(self):
        empty = self.base / "empty"
        empty.mkdir()
        self.assertEqual(check.lint_plugin(empty)[1], 2)

    def test_license_in_archive(self):
        (self.plugin / "LICENSE").write_text("우리 라이선스")
        self.assertEqual(len(self.pack(["main.php", "LICENSE"])["files"]), 2)

    def test_bad_manifest_shape(self):
        self.manifest.write_text("[]")
        with self.assertRaises(check.CheckError):
            check.package_plugin(self.plugin, self.manifest, self.output)

if __name__ == "__main__":
    unittest.main()
