const CACHE_VERSION="mini-game-v10";

self.addEventListener("install",event=>{
  self.skipWaiting();
});

self.addEventListener("activate",event=>{
  event.waitUntil(
    caches.keys()
      .then(keys=>Promise.all(keys.filter(k=>k!==CACHE_VERSION).map(k=>caches.delete(k))))
      .then(()=>self.clients.claim())
  );
});

self.addEventListener("fetch",event=>{
  if(event.request.method!=="GET") return;

  const url=new URL(event.request.url);
  if(url.origin!==location.origin) return;

  // HTML luôn ưu tiên mạng để nhận bản mới nhất.
  if(event.request.mode==="navigate" || event.request.destination==="document"){
    event.respondWith(
      fetch(event.request,{cache:"no-store"})
        .then(resp=>{
          const copy=resp.clone();
          caches.open(CACHE_VERSION).then(c=>c.put(event.request,copy));
          return resp;
        })
        .catch(()=>caches.match(event.request).then(r=>r||caches.match("./index.html")))
    );
    return;
  }

  // Tài nguyên tĩnh: ưu tiên mạng, lỗi mới lấy cache.
  event.respondWith(
    fetch(event.request,{cache:"no-store"})
      .then(resp=>{
        const copy=resp.clone();
        caches.open(CACHE_VERSION).then(c=>c.put(event.request,copy));
        return resp;
      })
      .catch(()=>caches.match(event.request))
  );
});