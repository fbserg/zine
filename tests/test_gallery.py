"""Build the archive and check its deployable output."""
import json
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


class GalleryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['python3', 'scripts/site.py'], cwd=ROOT, check=True,
                       capture_output=True, text=True)

    def test_every_complete_issue_has_a_reader_and_eight_pages(self):
        expected = {path.parent.name for path in (ROOT / 'models').glob('*/8.jpg')}
        published = json.loads((ROOT / 'site/books.json').read_text())
        self.assertEqual(set(published), expected)
        for name in published:
            reader = (ROOT / 'site' / name / 'index.html').read_text()
            for page in range(1, 9):
                self.assertIn(f'src="{page}.jpg"', reader)
                self.assertEqual((ROOT / 'site' / name / f'{page}.jpg').read_bytes(),
                                 (ROOT / 'models' / name / f'{page}.jpg').read_bytes())
                self.assertTrue((ROOT / 'site' / name / f't{page}.jpg').is_file())

    def test_asset_header_patterns_use_at_most_one_wildcard(self):
        rules = (ROOT / 'site/_headers').read_text().splitlines()
        for rule in rules:
            if rule.startswith('/'):
                self.assertLessEqual(rule.count('*'), 1, rule)


if __name__ == '__main__':
    unittest.main()
