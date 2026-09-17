const CACHE_VERSION="game-ca-voi-v17";

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

  // Giữ link cũ nhưng chuyển hai game sang lớp đồng bộ Supabase.
  if(event.request.mode==="navigate"){
    let target=event.request;
    if(url.pathname.endsWith("/xep-khoi.html")){
      target=new Request(new URL("./xep-khoi-cloud.html?v=17",self.location).href,{method:"GET",credentials:"same-origin"});
    }else if(url.pathname.endsWith("/noi-so.html")){
      target=new Request(new URL("./noi-so-cloud.html?v=17",self.location).href,{method:"GET",credentials:"same-origin"});
    }

    event.respondWith(
      fetch(target,{cache:"no-store"})
        .then(resp=>{
          const copy=resp.clone();
          caches.open(CACHE_VERSION).then(c=>c.put(target,copy));
          return resp;
        })
        .catch(async()=>{
          return (await caches.match(target)) ||
                 (await caches.match(event.request)) ||
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