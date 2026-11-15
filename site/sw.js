const CACHE_NAME = 'job-watcher-shell-v1';
const SCOPE = self.registration.scope;
const SHELL = ['index.html', 'browse.html', 'market.html', 'styles.css', 'app.js', 'demo-data.js', 'manifest.json'].map(file => new URL(file, SCOPE).toString());

self.addEventListener('install', event => {
  event.waitUntil(caches.open(CACHE_NAME).then(cache => cache.addAll(SHELL)));
  self.skipWaiting();
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys => Promise.all(keys.filter(key => key !== CACHE_NAME).map(key => caches.delete(key))))
  );
  self.clients.claim();
});

self.addEventListener('fetch', event => {
  const request = event.request;
  if (request.method !== 'GET') return;

  event.respondWith(
    fetch(request)
      .then(response => {
        const copy = response.clone();
        caches.open(CACHE_NAME).then(cache => cache.put(request, copy));
        return response;
      })
      .catch(() => caches.match(request).then(response => response || caches.match(new URL('index.html', SCOPE).toString())))
  );
});
