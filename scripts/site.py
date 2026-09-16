"""Render every book under models/ into site/ as a static gallery."""
import pathlib, re, shutil, html, json, subprocess
from PIL import Image
root = pathlib.Path(__file__).resolve().parent.parent
site = root / 'site'
if site.exists(): shutil.rmtree(site)
site.mkdir()

CSS = """
:root{--bg:#f4f2ec;--ink:#111;--mute:#666;--accent:#ff3d8a}
@media (prefers-color-scheme:dark){:root{--bg:#1c1b19;--ink:#eee;--mute:#aaa}}
body{margin:0;background:var(--bg);color:var(--ink);font-family:"Courier New",Courier,monospace;padding-block:32px;padding-inline:16px}
main{max-width:960px;margin:0 auto}
h1{font:900 28px/1 Arial,sans-serif;letter-spacing:-.02em;margin:0 0 36px;border-bottom:6px solid var(--accent);display:inline-block;padding-bottom:4px}
h1.page-title{margin:0 0 18px}
a{color:inherit;text-decoration:none}
.book{display:block;margin:0 0 36px}
.meta{font-size:13px;color:var(--mute);margin:0 0 8px}
.book .meta b{color:var(--ink)}
.meta.foot{margin-top:48px}
.how{margin:-8px 0 16px}
.showp{cursor:pointer;font-weight:400;color:var(--mute)}
.showp:hover{color:var(--ink)}
.strip{display:grid;grid-template-columns:repeat(8,1fr);gap:4px}
.strip img{width:100%;height:auto;aspect-ratio:1;object-fit:cover;display:block;background:#fff}
@media(max-width:600px){.strip{grid-template-columns:repeat(8,minmax(72px,1fr));overflow-x:auto;scroll-snap-type:x mandatory;margin-inline:-16px;padding-inline:16px;gap:3px}.strip img{scroll-snap-align:start}}
.pages{max-width:640px;margin:0 auto;display:flex;flex-direction:column;gap:12px}
.pages img{width:100%;height:auto;aspect-ratio:1;display:block;box-shadow:0 1px 3px rgba(0,0,0,.15)}
@media (prefers-color-scheme:dark){.pages img{box-shadow:0 1px 3px rgba(0,0,0,.6)}}
.back{font-size:12px;color:var(--mute);display:inline-block;margin:0 0 20px}
.votes{display:inline-flex;gap:0;margin-inline-start:8px}
.votes button{font:inherit;font-size:13px;color:var(--mute);background:none;border:none;cursor:pointer;padding:6px 8px;margin:-6px 0;min-width:44px}
.votes button.active{color:var(--accent);font-weight:700}
.sort{margin-inline-start:8px}
.sort b{font-weight:400;cursor:pointer;color:var(--mute)}
.sort b.on{color:var(--ink);border-bottom:2px solid var(--accent);cursor:pointer}
.comments{max-width:640px;margin:24px auto 0}
.ideas{position:fixed;right:16px;bottom:calc(16px + env(safe-area-inset-bottom,0px));max-width:300px;background:var(--bg);padding:6px 10px;border:1px solid var(--mute)}
.ideas summary{cursor:pointer;list-style:none;margin:0}
.ideas summary::-webkit-details-marker{display:none}
.ideas .comments{margin:8px 0 0;max-height:40vh;overflow-y:auto}
@media(max-width:600px){.ideas{left:16px;max-width:none}}
.comments p.meta{margin:0 0 6px}
.comments input{font:inherit;font-size:13px;color:var(--ink);background:none;border:none;border-bottom:1px solid var(--mute);width:100%;padding:6px 0}
.idea b{cursor:pointer;font-weight:400}
.idea b.active{color:var(--accent);font-weight:700}
.fave{cursor:pointer;margin-inline-start:6px;color:var(--mute)}
.fave.on{color:var(--accent)}
"""
JS = """<script>
(function(){
  function apply(el,c,mine){el.querySelector('[data-dir=up] b').textContent=c.up||0;el.querySelector('[data-dir=down] b').textContent=c.down||0;el.querySelectorAll('button').forEach(b=>b.classList.toggle('active',b.dataset.dir===mine))}
  var sortEl=document.querySelector('.sort'), mode='votes';
  function score(r){return +r.querySelector('[data-dir=up] b').textContent-r.querySelector('[data-dir=down] b').textContent}
  function faves(){try{return JSON.parse(localStorage.getItem('faves')||'[]')}catch(e){return []}}
  function setFaves(v){try{localStorage.setItem('faves',JSON.stringify(v))}catch(e){}}
  function sortRows(){
    var rows=[...document.querySelectorAll('.book')], foot=document.querySelector('.meta.foot'), f=faves();
    rows.sort((a,b)=>{
      if(mode==='new') return a.dataset.idx-b.dataset.idx;
      if(mode==='faves'){var d=f.includes(b.querySelector('.votes').dataset.book)-f.includes(a.querySelector('.votes').dataset.book); if(d) return d}
      return score(b)-score(a)||b.dataset.ts-a.dataset.ts;
    });
    rows.forEach(r=>foot.parentNode.insertBefore(r,foot));
  }
  document.querySelectorAll('.fave').forEach(f=>f.classList.toggle('on',faves().includes(f.dataset.book))&&(f.textContent=f.classList.contains('on')?'♥':'♡'));
  if(sortEl){
    try{mode=localStorage.getItem('sort')||'votes'}catch(e){}
    sortEl.querySelectorAll('b').forEach(b=>b.classList.toggle('on',b.dataset.sort===mode));
    sortEl.addEventListener('click',e=>{var b=e.target.closest('b'); if(!b) return; mode=b.dataset.sort;
      sortEl.querySelectorAll('b').forEach(x=>x.classList.toggle('on',x===b)); sortRows(); try{localStorage.setItem('sort',mode)}catch(e){}});
  }
  fetch('/api/votes').then(r=>r.json()).then(d=>{document.querySelectorAll('.votes').forEach(el=>apply(el,d.counts[el.dataset.book]||{},d.mine[el.dataset.book])); if(sortEl) sortRows();});
  document.addEventListener('click',e=>{
    var f=e.target.closest('.fave');
    if(f){var v=faves(),i=v.indexOf(f.dataset.book); i<0?v.push(f.dataset.book):v.splice(i,1);
      f.classList.toggle('on',i<0); f.textContent=i<0?'♥':'♡'; setFaves(v); if(mode==='faves') sortRows(); return}
    var b=e.target.closest('.votes button'); if(!b) return;
    e.preventDefault(); e.stopPropagation();
    fetch('/api/vote',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:b.closest('.votes').dataset.book,dir:b.dataset.dir})})
      .then(r=>r.json()).then(d=>apply(b.closest('.votes'),d,d.mine));
  });
  document.querySelectorAll('.comments').forEach(function(box){
    var list = box.querySelector('.list'), name = box.dataset.book, idea = name === '_ideas';
    function load(){fetch('/api/comments?name='+encodeURIComponent(name)).then(r=>r.json()).then(render)}
    function render(cs){list.innerHTML=cs.slice(-50).map(function(c){
      var t=c.t.replace(/</g,'&lt;');
      return idea?'<p class="meta idea" data-at="'+c.at+'"><b class="up'+(c.mine?' active':'')+'">▲</b> '+(c.n||0)+' '+t+'</p>':'<p class="meta">'+t+'</p>';
    }).join('')}
    load();
    box.querySelector('input').addEventListener('keydown',function(e){
      if (e.key !== 'Enter' || !this.value.trim()) return;
      var text = this.value.trim().slice(0,140); this.value='';
      fetch('/api/comment',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:name,text:text})})
        .then(r=>r.ok?load():null);
    });
    if (idea) box.addEventListener('click',function(e){
      var b=e.target.closest('.idea b'); if(!b) return;
      fetch('/api/idea-vote',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({at:+b.closest('.idea').dataset.at})}).then(load);
    });
  });
})();
</script>"""
FAVICON = "<link rel=\"icon\" href=\"data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 16 16'><rect width='16' height='16' fill='%23f4f2ec'/><text x='2' y='13' font-family='Arial' font-weight='900' font-size='13' fill='%23111'>U</text></svg>\">"
def head(title, image):
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(title)}</title>'
            f'{FAVICON}<meta property="og:title" content="{html.escape(title)}">'
            f'<meta property="og:image" content="https://zine.serg.lol/{image}">'
            f'<style>{CSS}</style></head><body><main>')
def votes(name): return f'<span class="votes" data-book="{html.escape(name)}"><button data-dir="up">▲ <b>0</b></button><button data-dir="down">▼ <b>0</b></button></span>'

# Every version of the rules ever committed, so old books' seeds still separate from the rules they were made under.
_revs = subprocess.run(['git', 'log', '--format=%H', '--', 'direction/RULES.md'], capture_output=True, text=True, cwd=root).stdout.split()
RULES = set(l.strip() for l in (root / 'direction' / 'RULES.md').read_text().splitlines())
for _r in _revs:
    RULES |= set(l.strip() for l in subprocess.run(['git', 'show', f'{_r}:direction/RULES.md'], capture_output=True, text=True, cwd=root).stdout.splitlines())
def how_html(d, cost):
    """One mute line: the seed as typed, and who wrote the script."""
    dirfile = d / 'DIRECTION.md'
    seeds = [l.strip() for l in dirfile.read_text().splitlines() if l.strip() and l.strip() not in RULES] if dirfile.exists() else []
    def tidy(l):
        if l.startswith(('Made in', 'Ontario', 'North Florida', 'UNPROMPTED,', 'State your')): return None
        m = re.match(r'Compose every page as (.+?) would', l)
        if m: return 'as ' + m.group(1)
        l = re.sub(r'^This issue(, the (reference|vibe only))?:\s*', '', l).rstrip('.')
        return l
    seed = ' · '.join(html.escape(s) for s in (tidy(l) for l in seeds) if s) or 'seed not recorded'
    model = str((cost.get('editor') or {}).get('model', '')) if cost else ''
    short = re.sub(r'^claude-|-\d.*$', '', model) if model else ''
    body = seed + (f' · <b>{short}</b>' if short else '')
    return f'<p class="meta"><b class="showp" onclick="var h=this.parentNode.nextElementSibling;h.hidden=!h.hidden;this.textContent=h.hidden?\'show prompt\':\'hide prompt\'">show prompt</b></p><p class="meta how" hidden>{body}</p>'

books = []
for d in sorted(root.glob('models/*')):
    if not (d / '8.jpg').exists(): continue
    name = d.name
    ink = ''
    s = d / 'SCRIPT.md'
    if s.exists():
        m = re.match(r'Ink:\s*(.+)', s.read_text()); ink = m.group(1).strip() if m else ''
    ts = (subprocess.run(['git', 'log', '--follow', '--diff-filter=A', '--format=%ct', '--', str(d / '8.jpg')], capture_output=True, text=True, cwd=root).stdout.split() or ['0'])[-1]
    out = site / name; out.mkdir()
    for n in range(1, 9):
        src = d / f'{n}.jpg'
        shutil.copy(src, out / f'{n}.jpg')
        thumb = d / f't{n}.jpg'
        if not thumb.exists() or thumb.stat().st_mtime < src.stat().st_mtime:
            im = Image.open(src)
            im.thumbnail((240, 240))
            im.convert('RGB').save(thumb, 'JPEG', quality=78)
        shutil.copy(thumb, out / f't{n}.jpg')
    c = d / 'COST.json'
    cost = json.loads(c.read_text()) if c.exists() else None
    books.append(dict(name=name, ink=ink, ts=int(ts or 0), cost=cost))
    imgs = ''.join(
        f'<img src="{n}.jpg" alt="page {n}" width="1000" height="1000" decoding="async" loading="{"eager" if n <= 2 else "lazy"}">'
        for n in range(1, 9))
    (out / 'index.html').write_text(
        head(f'Unprompted / {name}', f'{name}/1.jpg') +
        f'<a class="back" href="../">← all issues</a>{votes(name)}<h1 class="page-title">{html.escape(name)}</h1>{how_html(d, cost)}<div class="pages">{imgs}</div>'
        f'<div class="comments" data-book="{html.escape(name)}"><div class="list"></div><input maxlength="140" placeholder="say something"></div>'
        f'</main>{JS}</body></html>')

books.sort(key=lambda b: -b['ts'])
def usd(b):
    c = b['cost']
    if not c: return ''
    return f' · ${c["usd"]:.2f}' + ('*' if c['partial'] else '') + f' · {c["draw"]["images"]} images' if c.get('draw') else f' · ${c["usd"]:.2f}*'
total = sum(b['cost']['usd'] for b in books if b['cost'])
rows = ''.join(
    f'<a class="book" href="{b["name"]}/" data-ts="{b["ts"]}" data-idx="{i}"><p class="meta"><b>{html.escape(b["name"])}</b>{usd(b)}{votes(b["name"])}<span class="fave" data-book="{html.escape(b["name"])}">♡</span></p><div class="strip">' +
    ''.join(f'<img src="{b["name"]}/t{n}.jpg" alt="" width="240" height="240" decoding="async" loading="lazy">' for n in range(1, 9)) + '</div></a>' for i, b in enumerate(books))
foot = f'<p class="meta foot">{len(books)} issues · ${total:.2f} in est. API tokens and images at list price, editor plus illustrator. * = editor not logged, draw only.</p>'
cover = f'{books[0]["name"]}/1.jpg' if books else ''
sort_toggle = '<span class="meta sort"><b data-sort="votes">votes</b> · <b data-sort="new">new</b> · <b data-sort="faves">faves</b></span>'
ideas = '<details class="ideas"><summary class="meta">suggest a prompt or style</summary><div class="comments" data-book="_ideas"><div class="list"></div><input maxlength="140" placeholder="suggest a prompt or style"></div></details>'
book_names = [b['name'] for b in books]
refresh_js = f"""<script>
(function(){{
  var known={json.dumps(book_names)};
  function reload(){{if(document.visibilityState==='visible'){{location.reload()}}else{{document.addEventListener('visibilitychange',reload,{{once:true}})}}}}
  setInterval(function(){{fetch('/books.json',{{cache:'no-store'}}).then(r=>r.json()).then(function(list){{
    if(JSON.stringify(list)!==JSON.stringify(known)) reload();
  }})}},60000);
}})();
</script>"""
(site / 'index.html').write_text(head('Unprompted', cover) + '<h1>UNPROMPTED</h1>' + sort_toggle + rows + ideas + foot + f'</main>{JS}{refresh_js}</body></html>')
(site / 'books.json').write_text(json.dumps(book_names))
(site / '_headers').write_text(
    '/\n  Cache-Control: public, max-age=300\n'
    '/:book/\n  Cache-Control: public, max-age=300\n'
    '/:book/*.jpg\n  Cache-Control: public, max-age=31536000, immutable\n'
    '/books.json\n  Cache-Control: no-store\n')
print(f'{len(books)} books')
