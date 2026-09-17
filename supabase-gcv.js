import { createClient } from "https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2.116.0/+esm";

const SUPABASE_URL = "https://vhlzfdjrresavnrwmlli.supabase.co";
const SUPABASE_PUBLISHABLE_KEY = "sb_publishable_sQURyY0guiUzpg2Ha-a0tA_m_kJMk1D";

const supabase = createClient(SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY, {
  auth: {
    persistSession: true,
    autoRefreshToken: true,
    detectSessionInUrl: true
  }
});

const accountUrl = new URL("./tai-khoan.html", window.location.href).href;

async function getUser() {
  const { data, error } = await supabase.auth.getUser();
  if (error && !String(error.message || "").toLowerCase().includes("session")) {
    console.warn("Không đọc được người dùng:", error.message);
  }
  return data?.user || null;
}

async function getProfile() {
  const user = await getUser();
  if (!user) return null;
  const { data, error } = await supabase
    .from("profiles")
    .select("user_id, display_name, avatar_url")
    .eq("user_id", user.id)
    .maybeSingle();
  if (error) {
    console.warn("Không đọc được hồ sơ:", error.message);
    return null;
  }
  return data || null;
}

async function signUp({ email, password, displayName }) {
  return supabase.auth.signUp({
    email: String(email || "").trim(),
    password: String(password || ""),
    options: {
      data: { display_name: String(displayName || "").trim() || "Người chơi" },
      emailRedirectTo: accountUrl
    }
  });
}

async function signIn({ email, password }) {
  return supabase.auth.signInWithPassword({
    email: String(email || "").trim(),
    password: String(password || "")
  });
}

async function signOut() {
  return supabase.auth.signOut();
}

async function updateDisplayName(displayName) {
  const user = await getUser();
  if (!user) return { error: new Error("Bạn chưa đăng nhập.") };
  const value = String(displayName || "").trim().slice(0, 40);
  if (!value) return { error: new Error("Tên hiển thị không được để trống.") };

  const { data, error } = await supabase
    .from("profiles")
    .update({ display_name: value, updated_at: new Date().toISOString() })
    .eq("user_id", user.id)
    .select("user_id, display_name, avatar_url")
    .single();

  if (!error) refreshUserBadges();
  return { data, error };
}

async function saveResult({ gameCode, score = 0, level = 1, durationMs = null, metadata = {} }) {
  const user = await getUser();
  if (!user) return { saved: false, reason: "not_signed_in" };

  const payload = {
    user_id: user.id,
    game_code: String(gameCode || "ca-voi"),
    score: Math.max(0, Math.round(Number(score) || 0)),
    level: Math.max(1, Math.round(Number(level) || 1)),
    duration_ms: durationMs == null ? null : Math.max(0, Math.round(Number(durationMs) || 0)),
    metadata: metadata && typeof metadata === "object" ? metadata : {}
  };

  const { data, error } = await supabase
    .from("game_results")
    .insert(payload)
    .select("id")
    .single();

  if (error) {
    console.warn("Không lưu được kết quả:", error.message);
    return { saved: false, reason: "error", error };
  }
  return { saved: true, id: data?.id };
}

async function searchPlayers(keyword) {
  const q = String(keyword || "").trim();
  if (!q) return [];
  const { data, error } = await supabase
    .from("profiles")
    .select("user_id, display_name, avatar_url")
    .ilike("display_name", `%${q.replace(/[%_]/g, "")}%`)
    .order("display_name", { ascending: true })
    .limit(20);
  if (error) throw error;
  return data || [];
}

async function getProfilesByIds(ids) {
  const unique = [...new Set((ids || []).filter(Boolean))];
  if (!unique.length) return new Map();
  const { data, error } = await supabase
    .from("profiles")
    .select("user_id, display_name, avatar_url")
    .in("user_id", unique);
  if (error) throw error;
  return new Map((data || []).map(x => [x.user_id, x]));
}

async function getXepKhoiLeaderboard(limit = 20) {
  const { data, error } = await supabase
    .from("game_results")
    .select("user_id, score, played_at")
    .eq("game_code", "xep-khoi")
    .order("score", { ascending: false })
    .limit(300);
  if (error) throw error;

  const best = new Map();
  for (const row of data || []) {
    const prev = best.get(row.user_id);
    if (!prev || row.score > prev.score) best.set(row.user_id, row);
  }

  const rows = [...best.values()]
    .sort((a, b) => b.score - a.score)
    .slice(0, limit);

  const profiles = await getProfilesByIds(rows.map(x => x.user_id));
  return rows.map((x, i) => ({
    rank: i + 1,
    user_id: x.user_id,
    display_name: profiles.get(x.user_id)?.display_name || "Người chơi",
    score: x.score
  }));
}

async function getTimSo20Leaderboard(limit = 20) {
  const { data, error } = await supabase
    .from("game_results")
    .select("user_id, duration_ms, metadata, played_at")
    .eq("game_code", "tim-so")
    .not("duration_ms", "is", null)
    .order("duration_ms", { ascending: true })
    .limit(500);
  if (error) throw error;

  const filtered = (data || []).filter(row => {
    const m = row.metadata || {};
    return (m.mode || "standard") === "standard" &&
      Number(m.range || 20) === 20 &&
      m.hint !== true;
  });

  const best = new Map();
  for (const row of filtered) {
    const prev = best.get(row.user_id);
    if (!prev || row.duration_ms < prev.duration_ms) best.set(row.user_id, row);
  }

  const rows = [...best.values()]
    .sort((a, b) => a.duration_ms - b.duration_ms)
    .slice(0, limit);

  const profiles = await getProfilesByIds(rows.map(x => x.user_id));
  return rows.map((x, i) => ({
    rank: i + 1,
    user_id: x.user_id,
    display_name: profiles.get(x.user_id)?.display_name || "Người chơi",
    duration_ms: x.duration_ms
  }));
}

async function getRecentResults(limit = 20) {
  const user = await getUser();
  if (!user) return [];
  const { data, error } = await supabase
    .from("game_results")
    .select("id, game_code, score, level, duration_ms, metadata, played_at")
    .eq("user_id", user.id)
    .order("played_at", { ascending: false })
    .limit(limit);
  if (error) throw error;
  return data || [];
}

async function refreshUserBadges() {
  let label = "Khách";
  let signedIn = false;
  try {
    const profile = await getProfile();
    if (profile?.display_name) {
      label = profile.display_name;
      signedIn = true;
    }
  } catch (_) {}

  document.querySelectorAll("[data-gcv-user]").forEach(el => {
    el.textContent = label;
  });
  document.querySelectorAll("[data-gcv-auth-state]").forEach(el => {
    el.textContent = signedIn ? "Đã đăng nhập" : "Chưa đăng nhập";
  });
}

const GCV = {
  supabase,
  getUser,
  getProfile,
  signUp,
  signIn,
  signOut,
  updateDisplayName,
  saveResult,
  searchPlayers,
  getXepKhoiLeaderboard,
  getTimSo20Leaderboard,
  getRecentResults,
  refreshUserBadges
};

window.GCV = GCV;
window.dispatchEvent(new CustomEvent("gcv-ready", { detail: GCV }));

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", refreshUserBadges);
} else {
  refreshUserBadges();
}

supabase.auth.onAuthStateChange(() => {
  setTimeout(refreshUserBadges, 0);
});

export { GCV };
