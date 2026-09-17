(()=>{
  let gameStartedAt=Date.now();

  function whenGCV(cb){
    if(window.GCV){cb(window.GCV);return;}
    window.addEventListener("gcv-ready",e=>cb(e.detail),{once:true});
  }

  function toast(text){
    let el=document.getElementById("gcvSyncToast");
    if(!el){
      el=document.createElement("div");
      el.id="gcvSyncToast";
      el.style.cssText="position:fixed;left:50%;bottom:16px;transform:translateX(-50%);z-index:20000;background:#111827dd;color:#fff;padding:9px 13px;border-radius:999px;font:700 12px Arial;box-shadow:0 5px 18px #0003;opacity:0;transition:.2s;pointer-events:none;white-space:nowrap";
      document.body.appendChild(el);
    }
    el.textContent=text;
    el.style.opacity="1";
    clearTimeout(el._t);
    el._t=setTimeout(()=>el.style.opacity="0",1500);
  }

  async function save(payload){
    whenGCV(async GCV=>{
      try{
        const r=await GCV.saveResult(payload);
        if(r?.saved) toast("☁️ Đã lưu kết quả");
      }catch(e){
        console.warn("Không đồng bộ được kết quả:",e);
      }
    });
  }

  function hookXepKhoi(){
    if(typeof window.gameover!=="function") return false;
    const original=window.gameover;
    window.gameover=function(){
      const score=Math.max(0,Number(document.getElementById("final")?.textContent||window.sc||0)||0);
      original.apply(this,arguments);
      save({
        gameCode:"xep-khoi",
        score,
        level:1,
        durationMs:Math.max(0,Date.now()-gameStartedAt),
        metadata:{source:"game-ca-voi",version:17}
      });
    };
    ["again","new"].forEach(id=>document.getElementById(id)?.addEventListener("click",()=>{gameStartedAt=Date.now()}));
    return true;
  }

  function hookTimSo(){
    if(typeof window.finish!=="function") return false;
    const original=window.finish;
    window.finish=function(){
      original.apply(this,arguments);
      const finalText=document.getElementById("finalTime")?.textContent||"0";
      const sec=parseFloat(String(finalText).replace(",","."))||0;
      const range=Math.max(5,Math.min(100,Number(document.getElementById("range")?.value)||20));
      const randomToggle=document.getElementById("random4Toggle");
      const hintToggle=document.getElementById("hintToggle");
      const isRandom=randomToggle?.classList.contains("on")||randomToggle?.getAttribute("aria-pressed")==="true";
      const hint=!!hintToggle?.classList.contains("on");
      const recordText=document.getElementById("recordText")?.textContent||"";
      const percentMatch=recordText.match(/(\d+)%/);
      const randomPercent=percentMatch?Number(percentMatch[1]):null;
      save({
        gameCode:"tim-so",
        score:Math.max(0,Math.round(range*1000-Math.round(sec*100))),
        level:range,
        durationMs:Math.max(0,Math.round(sec*1000)),
        metadata:{
          mode:isRandom?"random":"standard",
          range,
          hint,
          random_percent:randomPercent,
          source:"game-ca-voi",
          version:17
        }
      });
    };
    document.getElementById("again")?.addEventListener("click",()=>{gameStartedAt=Date.now()});
    document.getElementById("restart")?.addEventListener("click",()=>{gameStartedAt=Date.now()});
    return true;
  }

  function addAccountButton(){
    if(document.getElementById("gcvAccountBtn")) return;
    const btn=document.createElement("button");
    btn.id="gcvAccountBtn";
    btn.type="button";
    btn.textContent="👤";
    btn.title="Tài khoản & bảng xếp hạng";
    btn.style.cssText="position:fixed;right:10px;bottom:10px;width:46px;height:46px;border:0;border-radius:15px;background:#fff;color:#374151;font-size:22px;box-shadow:0 6px 20px #0003;z-index:15000";
    btn.onclick=()=>location.href="./tai-khoan.html";
    document.body.appendChild(btn);
  }

  function init(){
    addAccountButton();
    const path=location.pathname;
    if(path.endsWith("/xep-khoi.html")) hookXepKhoi();
    if(path.endsWith("/noi-so.html")) hookTimSo();
  }

  if(document.readyState==="loading") document.addEventListener("DOMContentLoaded",init);
  else init();
})();