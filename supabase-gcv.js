import { createClient } from "https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2.116.0/+esm";

const SUPABASE_URL = "https://vhlzfdjrresavnrwmlli.supabase.co";
const SUPABASE_PUBLISHABLE_KEY = "sb_publishable_sQURyY0guiUzpg2Ha-a0tA_m_kJMk1D";
const supabase = createClient(SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY,{auth:{persistSession:true,autoRefreshToken:true,detectSessionInUrl:true}});

function cleanName(v){return String(v||"").trim().replace(/\s+/g," ").slice(0,24)}
async function internalEmail(name){const n=cleanName(name).normalize("NFKC").toLocaleLowerCase("vi");const d=await crypto.subtle.digest("SHA-256",new TextEncoder().encode(n));const h=[...new Uint8Array(d)].map(b=>b.toString(16).padStart(2,"0")).join("");return `kid_${h}@game-ca-voi.local`}
function validPin(pin){return /^\d{4}$/.test(String(pin||""))}
function authPassword(pin){return `kid-${String(pin)}-gcv`}

function getRememberedPlayers(){
  try{
    const arr=JSON.parse(localStorage.getItem("gcvRememberedPlayers")||"[]");
    return Array.isArray(arr)?arr.filter(x=>x&&x.name).slice(0,6):[];
  }catch(_){return []}
}
function rememberPlayer(name){
  try{
    const n=cleanName(name);if(!n)return;
    const old=getRememberedPlayers().filter(x=>x.name.toLocaleLowerCase("vi")!==n.toLocaleLowerCase("vi"));
    localStorage.setItem("gcvRememberedPlayers",JSON.stringify([{name:n,last_used:Date.now()},...old].slice(0,6)));
    localStorage.setItem("gcvRememberedName",n);
  }catch(_){}
}
function forgetRememberedPlayer(name){
  try{
    const n=cleanName(name).toLocaleLowerCase("vi");
    const next=getRememberedPlayers().filter(x=>x.name.toLocaleLowerCase("vi")!==n);
    localStorage.setItem("gcvRememberedPlayers",JSON.stringify(next));
    if((localStorage.getItem("gcvRememberedName")||"").toLocaleLowerCase("vi")===n)localStorage.removeItem("gcvRememberedName");
  }catch(_){}
}
function getRememberedName(){try{return localStorage.getItem("gcvRememberedName")||getRememberedPlayers()[0]?.name||""}catch(_){return ""}}

async function getUser(){const {data}=await supabase.auth.getUser();return data?.user||null}
async function getProfile(){const user=await getUser();if(!user)return null;const {data,error}=await supabase.from("profiles").select("user_id,login_name,display_name,avatar_url").eq("user_id",user.id).maybeSingle();if(error)throw error;return data||null}

async function signUp({name,pin}){
  const loginName=cleanName(name);if(loginName.length<2)return {error:new Error("Tên cần ít nhất 2 ký tự.")};if(!validPin(pin))return {error:new Error("PIN phải gồm đúng 4 số.")};
  const res=await fetch(`${SUPABASE_URL}/functions/v1/register-child`,{method:"POST",headers:{"Content-Type":"application/json",apikey:SUPABASE_PUBLISHABLE_KEY},body:JSON.stringify({name:loginName,pin:String(pin)})});
  const json=await res.json().catch(()=>({}));if(!res.ok)return {error:new Error(json.error||"Không tạo được tài khoản.")};return signIn({name:loginName,pin});
}
async function signIn({name,pin}){
  const loginName=cleanName(name);if(loginName.length<2)return {error:new Error("Hãy nhập tên người chơi.")};if(!validPin(pin))return {error:new Error("PIN phải gồm đúng 4 số.")};
  const result=await supabase.auth.signInWithPassword({email:await internalEmail(loginName),password:authPassword(pin)});
  if(!result.error)rememberPlayer(loginName);
  return result;
}
async function signOut(){return supabase.auth.signOut()}

async function saveResult({gameCode,score=0,level=1,durationMs=null,metadata={}}){const user=await getUser();if(!user)return {saved:false,reason:"not_signed_in"};const {data,error}=await supabase.from("game_results").insert({user_id:user.id,game_code:String(gameCode||"ca-voi"),score:Math.max(0,Math.round(Number(score)||0)),level:Math.max(1,Math.round(Number(level)||1)),duration_ms:durationMs==null?null:Math.max(0,Math.round(Number(durationMs)||0)),metadata:metadata&&typeof metadata==="object"?metadata:{}}).select("id").single();return error?{saved:false,reason:"error",error}:{saved:true,id:data?.id}}
async function searchPlayers(keyword){const q=cleanName(keyword);if(!q)return[];const {data,error}=await supabase.from("profiles").select("user_id,display_name,avatar_url").ilike("display_name",`%${q.replace(/[%_]/g,"")}%`).order("display_name").limit(20);if(error)throw error;return data||[]}
async function getProfilesByIds(ids){const u=[...new Set((ids||[]).filter(Boolean))];if(!u.length)return new Map();const {data,error}=await supabase.from("profiles").select("user_id,display_name,avatar_url").in("user_id",u);if(error)throw error;return new Map((data||[]).map(x=>[x.user_id,x]))}
async function getXepKhoiLeaderboard(limit=20){const {data,error}=await supabase.from("game_results").select("user_id,score,played_at").eq("game_code","xep-khoi").order("score",{ascending:false}).limit(300);if(error)throw error;const best=new Map();for(const r of data||[]){const p=best.get(r.user_id);if(!p||r.score>p.score)best.set(r.user_id,r)}const rows=[...best.values()].sort((a,b)=>b.score-a.score).slice(0,limit),profiles=await getProfilesByIds(rows.map(x=>x.user_id));return rows.map((x,i)=>({rank:i+1,user_id:x.user_id,display_name:profiles.get(x.user_id)?.display_name||"Người chơi",score:x.score}))}
async function getTimSo20Leaderboard(limit=20){const {data,error}=await supabase.from("game_results").select("user_id,duration_ms,metadata,played_at").eq("game_code","tim-so").not("duration_ms","is",null).order("duration_ms",{ascending:true}).limit(500);if(error)throw error;const filtered=(data||[]).filter(r=>{const m=r.metadata||{};return(m.mode||"standard")==="standard"&&Number(m.range||20)===20&&m.hint!==true});const best=new Map();for(const r of filtered){const p=best.get(r.user_id);if(!p||r.duration_ms<p.duration_ms)best.set(r.user_id,r)}const rows=[...best.values()].sort((a,b)=>a.duration_ms-b.duration_ms).slice(0,limit),profiles=await getProfilesByIds(rows.map(x=>x.user_id));return rows.map((x,i)=>({rank:i+1,user_id:x.user_id,display_name:profiles.get(x.user_id)?.display_name||"Người chơi",duration_ms:x.duration_ms}))}
async function getRecentResults(limit=20){const user=await getUser();if(!user)return[];const {data,error}=await supabase.from("game_results").select("id,game_code,score,level,duration_ms,metadata,played_at").eq("user_id",user.id).order("played_at",{ascending:false}).limit(limit);if(error)throw error;return data||[]}
async function refreshUserBadges(){let label="Khách",signed=false;try{const p=await getProfile();if(p?.display_name){label=p.display_name;signed=true;rememberPlayer(p.display_name)}}catch(_){}document.querySelectorAll("[data-gcv-user]").forEach(el=>el.textContent=label);document.querySelectorAll("[data-gcv-auth-state]").forEach(el=>el.textContent=signed?"Đã đăng nhập":"Chưa đăng nhập")}

const GCV={supabase,getUser,getProfile,signUp,signIn,signOut,getRememberedName,getRememberedPlayers,forgetRememberedPlayer,saveResult,searchPlayers,getXepKhoiLeaderboard,getTimSo20Leaderboard,getRecentResults,refreshUserBadges};window.GCV=GCV;window.dispatchEvent(new CustomEvent("gcv-ready",{detail:GCV}));if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",refreshUserBadges);else refreshUserBadges();supabase.auth.onAuthStateChange(()=>setTimeout(refreshUserBadges,0));export{GCV};