const CACHE_VERSION="game-ca-voi-v17";
const GAME_PAGES=new Set(["/xep-khoi/xep-khoi.html","/xep-khoi/noi-so.html"]);
const INJECT=`\n<script type="module" src="./supabase-gcv.js?v=17"></script>\n<script src="./game-sync.js?v=17"></script>\n`;

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

async function injectGameScripts(response,url){
  if(!response||!response.ok||!GAME_PAGES.has(url.pathname)) return response;
  const type=response.headers.get("content-type")||"";
  if(!type.includes("text/html")) return response;
  let html=await response.text();
  if(!html.includes("game-sync.js")) html=html.replace("</body>",INJECT+"</body>");
  const headers=new Headers(response.headers);
  headers.delete("content-length");
  return new Response(html,{status:response.status,statusText:response.statusText,headers});
}

async function networkFirst(request){
  try{
    const resp=await fetch(request,{cache:"no-store"});
    const copy=resp.clone();
    caches.open(CACHE_VERSION).then(c=>c.put(request,copy));
    return resp;
  }catch(_){
    return (await caches.match(request)) ||
           (await caches.match("./index.html")) ||
           Response.error();
  }
}

self.addEventListener("fetch",event=>{
  if(event.request.method!=="GET") return;

  const url=new URL(event.request.url);
  if(url.origin!==self.location.origin) return;

  if(event.request.mode==="navigate"){
    event.respondWith((async()=>injectGameScripts(await networkFirst(event.request),url))());
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