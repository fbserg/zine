// Upvote/downvote counts per book. One vote per browser via an HttpOnly cookie.
function vid(req) {
  const m = (req.headers.get('Cookie') || '').match(/(?:^|; )vid=([^;]+)/);
  return m ? m[1] : crypto.randomUUID();
}
async function getJson(env, key) {
  const raw = await env.VOTES.get(key);
  return raw ? JSON.parse(raw) : {};
}

export default {
  async fetch(req, env) {
    const url = new URL(req.url);
    const id = vid(req);
    const headers = new Headers({ 'Content-Type': 'application/json' });
    headers.set('Set-Cookie', `vid=${id}; HttpOnly; SameSite=Lax; Path=/; Max-Age=31536000`);

    if (url.pathname === '/api/votes' && req.method === 'GET') {
      const [counts, mine] = await Promise.all([getJson(env, 'counts'), getJson(env, `v:${id}`)]);
      return new Response(JSON.stringify({ counts, mine }), { headers });
    }

    if (url.pathname === '/api/vote' && req.method === 'POST') {
      const { name, dir } = await req.json();
      if (!name || (dir !== 'up' && dir !== 'down')) throw new Error('bad vote payload');
      const [counts, mine] = await Promise.all([getJson(env, 'counts'), getJson(env, `v:${id}`)]);
      const c = counts[name] || { up: 0, down: 0 };
      const prev = mine[name];
      const cleared = prev === dir;
      if (cleared) {
        c[dir]--;
        delete mine[name];
      } else {
        if (prev === 'up' || prev === 'down') c[prev]--;
        c[dir]++;
        mine[name] = dir;
      }
      counts[name] = c;
      await Promise.all([env.VOTES.put('counts', JSON.stringify(counts)), env.VOTES.put(`v:${id}`, JSON.stringify(mine))]);
      return new Response(JSON.stringify({ ...c, mine: cleared ? null : dir }), { headers });
    }

    if (url.pathname === '/api/comments' && req.method === 'GET') {
      const name = url.searchParams.get('name');
      if (!name) throw new Error('missing name');
      const list = JSON.parse(await env.VOTES.get(`c:${name}`) || '[]');
      const shape = name === '_ideas'
        ? c => ({ t: c.t, at: c.at, n: (c.u || []).length, mine: (c.u || []).includes(id) })
        : ({ t, at }) => ({ t, at });
      return new Response(JSON.stringify(list.map(shape)), { headers });
    }

    if (url.pathname === '/api/comment' && req.method === 'POST') {
      const { name, text } = await req.json();
      const t = (text || '').trim();
      if (!name || !t || t.length > 140) throw new Error('bad comment payload');
      const list = JSON.parse(await env.VOTES.get(`c:${name}`) || '[]');
      const last = [...list].reverse().find(c => c.v === id);
      const now = Date.now();
      if (last && now - last.at < 30000) return new Response(JSON.stringify({ error: 'rate limited' }), { status: 429, headers });
      list.push({ t, v: id, at: now });
      await env.VOTES.put(`c:${name}`, JSON.stringify(list.slice(-50)));
      return new Response(JSON.stringify({ t, at: now }), { headers });
    }

    if (url.pathname === '/api/idea-vote' && req.method === 'POST') {
      const { at } = await req.json();
      const list = JSON.parse(await env.VOTES.get('c:_ideas') || '[]');
      const c = list.find(c => c.at === at);
      if (!c) throw new Error('unknown idea');
      c.u = c.u || [];
      const i = c.u.indexOf(id);
      i === -1 ? c.u.push(id) : c.u.splice(i, 1);
      await env.VOTES.put('c:_ideas', JSON.stringify(list));
      return new Response(JSON.stringify({ at, n: c.u.length, mine: i === -1 }), { headers });
    }

    return env.ASSETS.fetch(req);
  },
};
