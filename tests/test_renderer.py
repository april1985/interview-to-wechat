import base64
from html.parser import HTMLParser
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('renderer', ROOT / 'scripts/render_article.py')
RENDERER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RENDERER)


class ImageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.images = []

    def handle_starttag(self, tag, attrs):
        if tag == 'img':
            self.images.append(dict(attrs))


class RendererTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / 'article.json'

    def render(self, blocks):
        self.source.write_text(json.dumps({'title': '示例', 'blocks': blocks}), encoding='utf-8')
        return RENDERER.render(self.source)

    def test_escapes_html_and_preserves_plain_text(self):
        html, text = self.render([{'type': 'p', 'text': '**重点** <script>alert(1)</script>'}])
        self.assertNotIn('<script>alert(1)</script>', html.read_text(encoding='utf-8'))
        self.assertIn('&lt;script&gt;', html.read_text(encoding='utf-8'))
        self.assertIn('重点 <script>', text.read_text(encoding='utf-8'))

    def test_local_image_is_embedded(self):
        # One-pixel PNG, with no private or external image dependency.
        image = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII=')
        (self.root / 'pixel.png').write_bytes(image)
        html, _ = self.render([{'type': 'image', 'path': 'pixel.png', 'alt': '示例'}])
        parser = ImageParser()
        parser.feed(html.read_text(encoding='utf-8'))
        self.assertEqual(base64.b64decode(parser.images[0]['src'].split(',', 1)[1]), image)

    def test_unknown_block_is_rejected(self):
        with self.assertRaises(ValueError):
            self.render([{'type': 'unsupported'}])


if __name__ == '__main__':
    unittest.main()
