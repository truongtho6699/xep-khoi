const CACHE_VERSION="game-ca-voi-v24";
const GAME_PAGES=new Set(["/xep-khoi/xep-khoi.html","/xep-khoi/noi-so.html"]);
const FIT_PAGES=new Set(["/xep-khoi/caro.html","/xep-khoi/lat-the.html","/xep-khoi/ghep-hinh.html","/xep-khoi/me-cung.html","/xep-khoi/dem-nhanh.html","/xep-khoi/tim-khac-nhau.html"]);
const CORE_ASSETS=["./","./index.html","./caro.html","./lat-the.html","./ghep-hinh.html","./me-cung.html","./dem-nhanh.html","./tim-khac-nhau.html","./kid-game-fit.css"];
const INJECT=`\n<script type="module" src="./supabase-gcv.js?v=20"></script>\n<script src="./game-sync.js?v=20"></script>\n`;
const FIT_LINK='<link rel="stylesheet" href="./kid-game-fit.css?v=24">';

self.addEventListener("install",event=>{event.waitUntil(caches.open(CACHE_VERSION).then(c=>c.addAll(CORE_ASSETS)).catch(()=>{}).then(()=>self.skipWaiting()));});
self.addEventListener("activate",event=>{event.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(k=>k!==CACHE_VERSION).map(k=>caches.delete(k)))).then(()=>self.clients.claim()));});

async function adaptHtml(response,url){
  if(!response||!response.ok)return response;
  const type=response.headers.get("content-type")||"";
  if(!type.includes("text/html"))return response;
  let html=await response.text();
  if(GAME_PAGES.has(url.pathname)&&!html.includes("game-sync.js"))html=html.replace("</body>",INJECT+"</body>");
  if(FIT_PAGES.has(url.pathname)&&!html.includes("kid-game-fit.css"))html=html.replace("</head>",FIT_LINK+"</head>");
  const headers=new Headers(response.headers);headers.delete("content-length");
  return new Response(html,{status:response.status,statusText:response.statusText,headers});
}

async function networkFirst(request){
  try{const resp=await fetch(request,{cache:"no-store"});const copy=resp.clone();caches.open(CACHE_VERSION).then(c=>c.put(request,copy));return resp}
  catch(_){return(await caches.match(request))||(await caches.match("./index.html"))||Response.error()}
}

self.addEventListener("fetch",event=>{
  if(event.request.method!=="GET")return;
  const url=new URL(event.request.url);
  if(url.origin!==self.location.origin)return;
  if(event.request.mode==="navigate"){
    event.respondWith((async()=>adaptHtml(await networkFirst(event.request),url))());
    return;
  }
  event.respondWith(fetch(event.request,{cache:"no-store"}).then(resp=>{const copy=resp.clone();caches.open(CACHE_VERSION).then(c=>c.put(event.request,copy));return resp}).catch(()=>caches.match(event.request)));
});