"""Render a local, public-safe article JSON with local images; standard library only."""
import argparse
import base64
from html import escape
import json
from pathlib import Path
import re

P_STYLE = 'margin:0 0 22px;font-size:16px;line-height:1.95;letter-spacing:.5px;color:#333d42;word-break:break-word;'


def rich(text):
    return re.sub(r'\*\*(.+?)\*\*', r'<strong style="color:#155c58;">\1</strong>', escape(text))


def render(source):
    data = json.loads(source.read_text(encoding='utf-8'))
    title = data['title']
    if not isinstance(title, str) or not title.strip():
        raise ValueError('title must be a nonempty string')
    if not isinstance(data['blocks'], list) or not data['blocks']:
        raise ValueError('blocks must be a nonempty list')
    parts, plain = [], [title]
    summary = data.get('summary', '')
    if summary:
        parts.append('<section style="margin:16px 0 38px;color:#655f59;">'
                     '<p style="margin:0;font-size:30px;line-height:1;">↱</p>'
                     '<p style="margin:3px 15px;font-size:16px;line-height:1.95;color:#49433e;">'
                     + rich(summary) + '</p>'
                     '<p style="margin:0;text-align:right;font-size:30px;line-height:1;">↲</p></section>')
        plain.append(summary)
    mime_types = {'.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.webp': 'image/webp'}
    for block in data['blocks']:
        kind = block['type']
        text = block.get('text', '')
        if kind == 'p':
            parts.append(f'<p style="{P_STYLE}">{rich(text)}</p>')
        elif kind == 'part':
            number = escape(str(block['number']))
            parts.append('<section style="margin:48px 0 28px;padding-bottom:15px;border-bottom:1px solid #dce8e3;">'
                         '<h2 style="margin:0;font-size:24px;line-height:1.7;font-weight:600;color:#155c58;">'
                         f'<span style="display:inline-block;margin-right:16px;font-family:Georgia,serif;font-size:34px;font-weight:400;color:#dfa17b;">{number}</span>'
                         + rich(text) + '</h2></section>')
            text = str(block['number']) + ' ' + text
        elif kind == 'subhead':
            parts.append('<h3 style="margin:30px 0 18px;font-size:18px;line-height:1.7;font-weight:600;color:#294a49;">' + rich(text) + '</h3>')
        elif kind == 'quote':
            parts.append('<section style="margin:26px 0;padding:19px 20px;background:#eef6f3;border-left:3px solid #267e78;">'
                         '<p style="margin:0;font-size:18px;line-height:1.9;color:#174d4c;">' + rich(text) + '</p></section>')
        elif kind == 'card':
            items = block['items']
            parts.append('<section style="margin:26px 0;padding:22px 20px;background:#fbf4ea;">'
                         '<p style="margin:0 0 15px;font-size:14px;font-weight:600;color:#ac581f;">' + rich(block['title']) + '</p>'
                         + ''.join('<p style="margin:0 0 10px;font-size:15px;line-height:1.9;color:#57483e;">' + rich(item) + '</p>' for item in items) + '</section>')
            text = block['title'] + '\n' + '\n'.join(items)
        elif kind == 'image':
            image_path = Path(block['path'])
            if not image_path.is_absolute():
                image_path = source.parent / image_path
            mime = mime_types.get(image_path.suffix.lower())
            if not mime:
                raise ValueError('Unsupported local image: ' + str(image_path))
            encoded = base64.b64encode(image_path.read_bytes()).decode('ascii')
            alt = escape(block['alt'], quote=True)
            parts.append(f'<section style="margin:28px 0;"><img src="data:{mime};base64,{encoded}" alt="{alt}" style="display:block;width:100%;max-width:100%;height:auto;border:0;"></section>')
            text = '[配图] ' + block['alt']
        elif kind == 'note':
            parts.append('<p style="margin:34px 0 0;padding-top:18px;border-top:1px solid #e4eae8;font-size:12px;line-height:1.9;color:#87918f;">' + rich(text) + '</p>')
        else:
            raise ValueError('Unsupported block type: ' + str(kind))
        plain.append(text.replace('**', ''))

    body = '\n'.join(parts)
    label = escape(data.get('label', '访谈与实践'))
    html = '''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>''' + escape(title) + '''</title>
<style>body{margin:0;background:#f1f3f1;font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif}.shell{max-width:730px;margin:28px auto 48px;background:white;padding:40px 48px;box-sizing:border-box}.tools{max-width:730px;margin:20px auto;padding:0 16px;box-sizing:border-box;font-size:12px;color:#748581}button{border:0;border-radius:5px;background:#155c58;color:white;padding:11px 18px;font-size:14px;cursor:pointer}h1{font-size:29px;line-height:1.55;color:#153c40;margin:12px 0 20px}@media(max-width:600px){.shell{margin:16px auto 0;padding:28px 23px}h1{font-size:26px}}@media print{.tools{display:none}body{background:white}.shell{margin:0;padding:0}}</style></head><body>
<div class="tools"><button onclick="copyArticle()">复制排版正文</button><p id="status" role="status" aria-live="polite">标题单独填写；图片建议单独上传，粘贴后检查样式。</p></div>
<main class="shell"><p style="font-size:11px;letter-spacing:2px;color:#a2683b;">''' + label + '</p><h1>' + escape(title) + '''</h1><article id="article" style="font-size:16px;line-height:1.95;font-family:-apple-system,BlinkMacSystemFont,'PingFang SC','Microsoft YaHei',sans-serif;">''' + body + '''</article></main>
<script>async function copyArticle(){const el=document.getElementById('article'),s=document.getElementById('status');try{if(navigator.clipboard&&window.ClipboardItem){await navigator.clipboard.write([new ClipboardItem({'text/html':new Blob([el.outerHTML],{type:'text/html'}),'text/plain':new Blob([el.innerText],{type:'text/plain'})})]);}else{const r=document.createRange();r.selectNodeContents(el);const sel=window.getSelection();sel.removeAllRanges();sel.addRange(r);if(!document.execCommand('copy'))throw Error('copy');sel.removeAllRanges();}s.textContent='正文已复制。图片建议单独上传，粘贴后检查样式。';}catch(e){const r=document.createRange();r.selectNodeContents(el);const sel=window.getSelection();sel.removeAllRanges();sel.addRange(r);s.textContent='正文已选中，请按 ⌘C 或 Ctrl+C 复制。';}}</script></body></html>'''
    html_path = source.parent / '公众号文章.html'
    text_path = source.parent / '公众号文章.txt'
    html_path.write_text(html, encoding='utf-8')
    text_path.write_text('\n\n'.join(plain) + '\n', encoding='utf-8')
    return html_path, text_path


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path, help='Public-safe article JSON with local image paths')
    args = parser.parse_args()
    for output in render(args.source.resolve()):
        print(output)
