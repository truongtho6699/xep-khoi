const CACHE_VERSION="game-ca-voi-v15";

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
  if(url.origin!==self.location.origin) return;

  // Mọi lần mở ứng dụng/trang đều ưu tiên bản trên mạng.
  if(event.request.mode==="navigate"){
    event.respondWith(
      fetch(event.request,{cache:"no-store"})
        .then(resp=>{
          const copy=resp.clone();
          caches.open(CACHE_VERSION).then(c=>c.put(event.request,copy));
          return resp;
        })
        .catch(async()=>{
          return (await caches.match(event.request)) ||
                 (await caches.match("./index.html")) ||
                 Response.error();
        })
    );
    return;
  }

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