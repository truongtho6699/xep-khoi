from pathlib import Path
import re
import sys

root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('.')
def p(name): return root / name
def read(name): return p(name).read_text(encoding='utf-8')
def write(name, s):
    p(name).parent.mkdir(parents=True, exist_ok=True)
    p(name).write_text(s, encoding='utf-8')

# 1) Thêm bảng điều khiển phòng chơi vào màn hình khởi động.
s = read('index.html')
room_ui = '''
          <div id="mp-panel" class="mp-panel">
            <div class="mp-title">👥 Chơi cùng nhau</div>
            <div id="mp-status" class="mp-status">Đang kiểm tra tài khoản…</div>
            <div id="mp-actions" class="mp-actions">
              <input id="mp-room-code" maxlength="8" inputmode="text" autocomplete="off" placeholder="Mã phòng, ví dụ CV1234" />
              <button id="mp-create-room" type="button">Tạo phòng</button>
              <button id="mp-join-room" type="button">Vào phòng</button>
            </div>
            <div id="mp-current" class="mp-current" hidden>
              <div>Phòng: <b id="mp-current-code">—</b> · <span id="mp-count">1 người</span></div>
              <div id="mp-player-list" class="mp-player-list"></div>
              <button id="mp-leave-room" type="button" class="mp-leave">Rời phòng</button>
            </div>
          </div>
'''
needle = '          <button id="play-button" type="button">▶ BẮT ĐẦU CHƠI</button>'
if room_ui.strip() not in s:
    s = s.replace(needle, room_ui + '\n' + needle)
write('index.html', s)

# 2) Mô-đun Supabase Realtime cho phòng, vị trí người chơi và khối xây dựng.
multiplayer_ts = r'''import * as THREE from "three";
import { createClient, type RealtimeChannel, type SupabaseClient } from "@supabase/supabase-js";
import type { World } from "./world/world";
import type { BlockId } from "./world/blocks";

const SUPABASE_URL = "https://vhlzfdjrresavnrwmlli.supabase.co";
const SUPABASE_PUBLISHABLE_KEY = "sb_publishable_sQURyY0guiUzpg2Ha-a0tA_m_kJMk1D";
const MOVE_INTERVAL_MS = 120;
const HEARTBEAT_MS = 30000;

type Vec3 = { x: number; y: number; z: number };
type MovePayload = { user_id: string; name: string; x: number; y: number; z: number; yaw: number; at: number };
type BlockPayload = { user_id: string; x: number; y: number; z: number; block_id: number; at: number };
type RoomRow = { id: string; code: string; world_seed: number; name: string; max_players: number };

type RemoteAvatar = {
  group: THREE.Group;
  target: THREE.Vector3;
  targetYaw: number;
  lastSeen: number;
};

export interface MultiplayerOptions {
  readonly scene: THREE.Scene | null;
  readonly world: World;
  readonly getPosition: () => Vec3;
  readonly getYaw: () => number;
  readonly recordEdit: (x: number, y: number, z: number, id: BlockId) => void;
  readonly refreshBlock: (x: number, y: number, z: number) => void;
}

export class BlockWorldMultiplayer {
  private readonly options: MultiplayerOptions;
  private readonly supabase: SupabaseClient;
  private channel: RealtimeChannel | null = null;
  private room: RoomRow | null = null;
  private userId = "";
  private displayName = "Người chơi";
  private joined = false;
  private lastMoveSent = 0;
  private lastHeartbeat = 0;
  private lastSentPosition = new THREE.Vector3(Number.NaN, Number.NaN, Number.NaN);
  private lastSentYaw = Number.NaN;
  private readonly avatars = new Map<string, RemoteAvatar>();
  private hud: HTMLDivElement | null = null;

  constructor(options: MultiplayerOptions) {
    this.options = options;
    this.supabase = createClient(SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY, {
      auth: { persistSession: true, autoRefreshToken: true, detectSessionInUrl: true },
    });
  }

  async init(): Promise<void> {
    this.bindUi();
    const { data: { user } } = await this.supabase.auth.getUser();
    if (!user) {
      this.setStatus('Chưa đăng nhập. Hãy đăng nhập Game Cá Voi để tạo hoặc vào phòng.', true);
      this.setActionsEnabled(false);
      const status = document.querySelector<HTMLElement>('#mp-status');
      if (status) status.innerHTML = 'Chưa đăng nhập. <a href="../tai-khoan.html">Đăng nhập Game Cá Voi</a> để chơi cùng nhau.';
      return;
    }
    this.userId = user.id;
    const { data: profile } = await this.supabase
      .from('profiles')
      .select('display_name')
      .eq('user_id', user.id)
      .maybeSingle();
    this.displayName = String(profile?.display_name || 'Người chơi');
    this.setStatus('Xin chào ' + this.displayName + '. Tạo phòng mới hoặc nhập mã phòng của bạn bè.');
    this.setActionsEnabled(true);
    this.createHud();

    const url = new URL(location.href);
    const pending = sessionStorage.getItem('bwPendingRoom') || '';
    const autoCode = (url.searchParams.get('room') || pending).trim().toUpperCase();
    if (autoCode) {
      sessionStorage.removeItem('bwPendingRoom');
      const input = document.querySelector<HTMLInputElement>('#mp-room-code');
      if (input) input.value = autoCode;
      await this.joinRoomByCode(autoCode, true);
    }
  }

  private bindUi(): void {
    const input = document.querySelector<HTMLInputElement>('#mp-room-code');
    input?.addEventListener('input', () => {
      input.value = input.value.toUpperCase().replace(/[^A-Z0-9]/g, '').slice(0, 8);
    });
    document.querySelector<HTMLButtonElement>('#mp-create-room')?.addEventListener('click', () => void this.createRoom());
    document.querySelector<HTMLButtonElement>('#mp-join-room')?.addEventListener('click', () => void this.joinRoomByCode(input?.value || ''));
    document.querySelector<HTMLButtonElement>('#mp-leave-room')?.addEventListener('click', () => void this.leaveRoom());
  }

  private setActionsEnabled(enabled: boolean): void {
    document.querySelectorAll<HTMLButtonElement>('#mp-actions button').forEach((b) => { b.disabled = !enabled; });
    const input = document.querySelector<HTMLInputElement>('#mp-room-code');
    if (input) input.disabled = !enabled;
  }

  private setStatus(message: string, error = false): void {
    const el = document.querySelector<HTMLElement>('#mp-status');
    if (!el) return;
    el.textContent = message;
    el.classList.toggle('error', error);
  }

  private randomCode(): string {
    const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';
    let out = 'CV';
    for (let i = 0; i < 4; i++) out += chars[Math.floor(Math.random() * chars.length)];
    return out;
  }

  async createRoom(): Promise<void> {
    if (!this.userId) return;
    this.setStatus('Đang tạo phòng…');
    for (let attempt = 0; attempt < 5; attempt++) {
      const code = this.randomCode();
      const { data, error } = await this.supabase
        .from('game_rooms')
        .insert({
          code,
          name: 'Phòng của ' + this.displayName,
          owner_id: this.userId,
          world_seed: this.options.world.seed,
          max_players: 8,
        })
        .select('id,code,world_seed,name,max_players')
        .single();
      if (!error && data) {
        const input = document.querySelector<HTMLInputElement>('#mp-room-code');
        if (input) input.value = data.code;
        await this.joinRoom(data as RoomRow);
        return;
      }
      if ((error as { code?: string } | null)?.code !== '23505') {
        this.setStatus('Không tạo được phòng. Hãy thử lại.', true);
        return;
      }
    }
    this.setStatus('Chưa tạo được mã phòng. Hãy bấm Tạo phòng lần nữa.', true);
  }

  async joinRoomByCode(rawCode: string, silent = false): Promise<void> {
    if (!this.userId) return;
    const code = rawCode.trim().toUpperCase();
    if (code.length < 4) {
      if (!silent) this.setStatus('Hãy nhập mã phòng.', true);
      return;
    }
    this.setStatus('Đang tìm phòng ' + code + '…');
    const { data, error } = await this.supabase
      .from('game_rooms')
      .select('id,code,world_seed,name,max_players')
      .eq('code', code)
      .maybeSingle();
    if (error || !data) {
      this.setStatus('Không tìm thấy phòng ' + code + '.', true);
      return;
    }
    await this.joinRoom(data as RoomRow);
  }

  private async joinRoom(room: RoomRow): Promise<void> {
    if (this.room?.id === room.id && this.joined) return;
    if (room.world_seed !== this.options.world.seed) {
      const url = new URL(location.href);
      url.searchParams.set('seed', String(room.world_seed));
      url.searchParams.set('room', room.code);
      sessionStorage.setItem('bwPendingRoom', room.code);
      location.replace(url.toString());
      return;
    }
    await this.leaveRoom(false);
    const { error } = await this.supabase.from('room_players').upsert({
      room_id: room.id,
      user_id: this.userId,
      display_name: this.displayName,
      last_seen: new Date().toISOString(),
    }, { onConflict: 'room_id,user_id' });
    if (error) {
      this.setStatus('Không vào được phòng. Hãy thử lại.', true);
      return;
    }
    this.room = room;
    const ok = await this.subscribeRoom(room);
    if (!ok) {
      this.setStatus('Không kết nối được phòng trực tuyến.', true);
      return;
    }
    this.joined = true;
    await this.loadWorldEdits();
    this.showCurrentRoom();
    this.setStatus('Đã vào phòng ' + room.code + '. Bạn bè dùng cùng mã này sẽ nhìn thấy nhau.');
    const url = new URL(location.href);
    url.searchParams.set('room', room.code);
    history.replaceState(null, '', url.toString());
  }

  private subscribeRoom(room: RoomRow): Promise<boolean> {
    return new Promise((resolve) => {
      const channel = this.supabase.channel('block-world:' + room.id, {
        config: { presence: { key: this.userId }, broadcast: { self: false } },
      });
      this.channel = channel;
      channel
        .on('presence', { event: 'sync' }, () => this.syncPresence())
        .on('broadcast', { event: 'move' }, ({ payload }) => this.receiveMove(payload as MovePayload))
        .on('broadcast', { event: 'block-edit' }, ({ payload }) => this.receiveBlockEdit(payload as BlockPayload))
        .subscribe(async (status) => {
          if (status === 'SUBSCRIBED') {
            const pos = this.options.getPosition();
            await channel.track({
              user_id: this.userId,
              name: this.displayName,
              x: pos.x,
              y: pos.y,
              z: pos.z,
              online_at: new Date().toISOString(),
            });
            resolve(true);
          } else if (status === 'CHANNEL_ERROR' || status === 'TIMED_OUT') {
            resolve(false);
          }
        });
    });
  }

  private syncPresence(): void {
    if (!this.channel) return;
    const state = this.channel.presenceState<Record<string, unknown>>();
    const live = new Map<string, string>();
    for (const entries of Object.values(state)) {
      for (const entry of entries) {
        const userId = String(entry.user_id || '');
        const name = String(entry.name || 'Người chơi');
        if (userId) live.set(userId, name);
      }
    }
    live.set(this.userId, this.displayName);
    for (const [id, avatar] of this.avatars) {
      if (!live.has(id)) {
        this.options.scene?.remove(avatar.group);
        this.avatars.delete(id);
      }
    }
    const names = [...live.entries()].map(([id, name]) => (id === this.userId ? name + ' (bạn)' : name));
    const list = document.querySelector<HTMLElement>('#mp-player-list');
    if (list) list.textContent = names.map((name) => '🟢 ' + name).join(' · ');
    const count = document.querySelector<HTMLElement>('#mp-count');
    if (count) count.textContent = names.length + ' người';
    this.updateHud(names.length);
  }

  private receiveMove(payload: MovePayload): void {
    if (!payload || payload.user_id === this.userId) return;
    let avatar = this.avatars.get(payload.user_id);
    if (!avatar) {
      avatar = this.createAvatar(payload.user_id, payload.name || 'Người chơi');
      if (!avatar) return;
      this.avatars.set(payload.user_id, avatar);
    }
    avatar.target.set(payload.x, payload.y, payload.z);
    avatar.targetYaw = payload.yaw;
    avatar.lastSeen = performance.now();
  }

  private createAvatar(userId: string, name: string): RemoteAvatar | null {
    const scene = this.options.scene;
    if (!scene) return null;
    let hash = 0;
    for (const ch of userId) hash = (hash * 31 + ch.charCodeAt(0)) >>> 0;
    const color = new THREE.Color().setHSL((hash % 360) / 360, 0.65, 0.55);
    const material = new THREE.MeshLambertMaterial({ color });
    const dark = new THREE.MeshLambertMaterial({ color: color.clone().multiplyScalar(0.72) });
    const group = new THREE.Group();
    const body = new THREE.Mesh(new THREE.BoxGeometry(0.7, 1.05, 0.38), material);
    body.position.y = 1.0;
    const head = new THREE.Mesh(new THREE.BoxGeometry(0.62, 0.62, 0.62), material);
    head.position.y = 1.83;
    const leg1 = new THREE.Mesh(new THREE.BoxGeometry(0.27, 0.78, 0.3), dark);
    leg1.position.set(-0.19, 0.39, 0);
    const leg2 = leg1.clone();
    leg2.position.x = 0.19;
    group.add(body, head, leg1, leg2, this.makeNameSprite(name));
    scene.add(group);
    return { group, target: new THREE.Vector3(), targetYaw: 0, lastSeen: performance.now() };
  }

  private makeNameSprite(name: string): THREE.Sprite {
    const canvas = document.createElement('canvas');
    canvas.width = 512;
    canvas.height = 96;
    const ctx = canvas.getContext('2d');
    if (ctx) {
      ctx.fillStyle = 'rgba(0,0,0,.62)';
      ctx.roundRect(4, 8, 504, 80, 20);
      ctx.fill();
      ctx.fillStyle = '#fff';
      ctx.font = 'bold 38px Arial';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(name.slice(0, 22), 256, 49);
    }
    const texture = new THREE.CanvasTexture(canvas);
    texture.colorSpace = THREE.SRGBColorSpace;
    const sprite = new THREE.Sprite(new THREE.SpriteMaterial({ map: texture, transparent: true, depthTest: false }));
    sprite.position.y = 2.55;
    sprite.scale.set(2.8, 0.53, 1);
    return sprite;
  }

  async publishBlockEdit(x: number, y: number, z: number, id: BlockId): Promise<void> {
    if (!this.joined || !this.room || !this.channel) return;
    const payload: BlockPayload = { user_id: this.userId, x, y, z, block_id: Number(id), at: Date.now() };
    void this.channel.send({ type: 'broadcast', event: 'block-edit', payload });
    const { error } = await this.supabase.from('world_edits').upsert({
      room_id: this.room.id,
      x, y, z,
      block_id: Number(id),
      updated_by: this.userId,
      updated_at: new Date().toISOString(),
    }, { onConflict: 'room_id,x,y,z' });
    if (error) console.warn('Không lưu được thay đổi khối:', error.message);
  }

  private receiveBlockEdit(payload: BlockPayload): void {
    if (!payload || payload.user_id === this.userId) return;
    this.applyEdit(payload.x, payload.y, payload.z, payload.block_id);
  }

  private applyEdit(x: number, y: number, z: number, blockId: number): void {
    const id = blockId as BlockId;
    this.options.world.setBlock(x, y, z, id);
    this.options.recordEdit(x, y, z, id);
    this.options.refreshBlock(x, y, z);
  }

  private async loadWorldEdits(): Promise<void> {
    if (!this.room) return;
    const { data, error } = await this.supabase
      .from('world_edits')
      .select('x,y,z,block_id')
      .eq('room_id', this.room.id)
      .limit(5000);
    if (error) {
      console.warn('Không tải được thế giới chung:', error.message);
      return;
    }
    for (const edit of data || []) this.applyEdit(edit.x, edit.y, edit.z, edit.block_id);
  }

  tick(now: number): void {
    for (const avatar of this.avatars.values()) {
      avatar.group.position.lerp(avatar.target, 0.28);
      const dy = Math.atan2(Math.sin(avatar.targetYaw - avatar.group.rotation.y), Math.cos(avatar.targetYaw - avatar.group.rotation.y));
      avatar.group.rotation.y += dy * 0.28;
    }
    if (!this.joined || !this.room || !this.channel) return;
    if (now - this.lastMoveSent >= MOVE_INTERVAL_MS) {
      const pos = this.options.getPosition();
      const yaw = this.options.getYaw();
      const changed = this.lastSentPosition.distanceToSquared(new THREE.Vector3(pos.x, pos.y, pos.z)) > 0.0004 || Math.abs(yaw - this.lastSentYaw) > 0.01;
      if (changed || now - this.lastMoveSent > 1000) {
        this.lastMoveSent = now;
        this.lastSentPosition.set(pos.x, pos.y, pos.z);
        this.lastSentYaw = yaw;
        void this.channel.send({
          type: 'broadcast',
          event: 'move',
          payload: { user_id: this.userId, name: this.displayName, x: pos.x, y: pos.y, z: pos.z, yaw, at: Date.now() } satisfies MovePayload,
        });
      }
    }
    if (now - this.lastHeartbeat >= HEARTBEAT_MS) {
      this.lastHeartbeat = now;
      void this.supabase.from('room_players').update({ last_seen: new Date().toISOString() }).eq('room_id', this.room.id).eq('user_id', this.userId);
    }
  }

  private showCurrentRoom(): void {
    const current = document.querySelector<HTMLElement>('#mp-current');
    if (current) current.hidden = false;
    const code = document.querySelector<HTMLElement>('#mp-current-code');
    if (code) code.textContent = this.room?.code || '—';
    if (this.hud) this.hud.hidden = false;
    this.updateHud(1);
  }

  private createHud(): void {
    if (this.hud) return;
    this.hud = document.createElement('div');
    this.hud.id = 'mp-hud';
    this.hud.hidden = true;
    document.body.appendChild(this.hud);
  }

  private updateHud(count: number): void {
    if (!this.hud || !this.room) return;
    this.hud.textContent = '👥 ' + this.room.code + ' · ' + count;
  }

  async leaveRoom(updateUrl = true): Promise<void> {
    const oldRoom = this.room;
    const oldChannel = this.channel;
    this.joined = false;
    this.channel = null;
    this.room = null;
    if (oldChannel) {
      try { await oldChannel.untrack(); } catch (_) { /* bỏ qua */ }
      await this.supabase.removeChannel(oldChannel);
    }
    if (oldRoom && this.userId) {
      void this.supabase.from('room_players').delete().eq('room_id', oldRoom.id).eq('user_id', this.userId);
    }
    for (const avatar of this.avatars.values()) this.options.scene?.remove(avatar.group);
    this.avatars.clear();
    const current = document.querySelector<HTMLElement>('#mp-current');
    if (current) current.hidden = true;
    if (this.hud) this.hud.hidden = true;
    if (updateUrl) {
      const url = new URL(location.href);
      url.searchParams.delete('room');
      history.replaceState(null, '', url.toString());
      this.setStatus('Đã rời phòng. Bạn có thể tạo hoặc vào phòng khác.');
    }
  }
}
'''
write('src/multiplayer.ts', multiplayer_ts)

# 3) Tích hợp mô-đun vào vòng lặp game.
s = read('src/main.ts')
if 'BlockWorldMultiplayer' not in s:
    s = s.replace('import { isTouchDevice, TouchControls } from "./ui/touch-controls";',
                  'import { isTouchDevice, TouchControls } from "./ui/touch-controls";\nimport { BlockWorldMultiplayer } from "./multiplayer";\nimport { worldToChunk } from "./world/coords";')

    s = s.replace('  let view: GameView;\n  let chunkMeshes: ChunkMeshManager | null = null;',
                  '  let view: GameView;\n  let multiplayerScene: THREE.Scene | null = null;\n  let chunkMeshes: ChunkMeshManager | null = null;')
    s = s.replace('    const gameScene = createGameScene(app);',
                  '    const gameScene = createGameScene(app);\n    multiplayerScene = gameScene.scene;')

    s = s.replace('  interaction.onEdit = (x, y, z, id) => {\n    editStore.record(x, y, z, id);\n  };',
'''  let multiplayer: BlockWorldMultiplayer | null = null;
  interaction.onEdit = (x, y, z, id) => {
    editStore.record(x, y, z, id);
    void multiplayer?.publishBlockEdit(x, y, z, id);
  };

  multiplayer = new BlockWorldMultiplayer({
    scene: multiplayerScene,
    world,
    getPosition: () => ({ ...player.position }),
    getYaw: () => player.eyeYaw,
    recordEdit: (x, y, z, id) => editStore.record(x, y, z, id),
    refreshBlock: (x, _y, z) => {
      const cx = worldToChunk(x);
      const cz = worldToChunk(z);
      for (const [dx, dz] of [[0, 0], [1, 0], [-1, 0], [0, 1], [0, -1]] as const) {
        if (world.hasChunk(cx + dx, cz + dz)) chunkMeshes?.updateChunk(cx + dx, cz + dz);
      }
    },
  });
  void multiplayer.init();''')

    s = s.replace('    view.render(elapsed);\n    requestAnimationFrame(frame);',
                  '    multiplayer?.tick(time);\n    view.render(elapsed);\n    requestAnimationFrame(frame);')
write('src/main.ts', s)

# 4) CSS cho bảng phòng chơi và trạng thái trong game.
s = read('src/style.css')
if '#mp-panel' not in s:
    s += r'''
/* ===== Chơi cùng nhau ===== */
#overlay-content{max-height:94vh;overflow:auto}
.mp-panel{margin:14px auto 4px;padding:12px;border-radius:16px;background:rgba(255,255,255,.09);border:1px solid rgba(255,255,255,.18);width:min(100%,520px)}
.mp-title{font-weight:900;font-size:17px;margin-bottom:6px}.mp-status{font-size:12px;line-height:1.4;color:#d7ecff}.mp-status.error{color:#ffd0d0}.mp-status a{color:#fff;font-weight:900}
.mp-actions{display:grid;grid-template-columns:1fr auto auto;gap:7px;margin-top:9px}.mp-actions input{min-width:0;border:0;border-radius:11px;padding:10px 11px;font-size:14px;text-transform:uppercase}.mp-actions button,.mp-leave{border:0;border-radius:11px;padding:10px 12px;font-weight:900;background:#eaf5ff;color:#16324a}.mp-actions button:disabled{opacity:.45}
.mp-current{margin-top:9px;font-size:13px}.mp-player-list{margin:7px 0;line-height:1.6;font-size:12px}.mp-leave{background:#ffdede;color:#7f1d1d}
#mp-hud{position:fixed;top:max(10px,env(safe-area-inset-top));right:max(10px,env(safe-area-inset-right));z-index:8;background:rgba(4,20,35,.72);color:#fff;border:1px solid rgba(255,255,255,.3);border-radius:999px;padding:7px 10px;font:800 12px Arial,sans-serif;pointer-events:none;text-shadow:0 1px 2px #000}
@media(pointer:coarse){.mp-actions{grid-template-columns:1fr 1fr}.mp-actions input{grid-column:1/-1}.mp-actions button{min-height:44px}#mp-hud{top:max(58px,calc(env(safe-area-inset-top) + 48px))}}
'''
write('src/style.css', s)

print('Đã thêm phòng chơi, nhìn thấy người khác và đồng bộ khối Block World.')
