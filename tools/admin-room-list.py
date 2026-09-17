from pathlib import Path
import sys

root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('.')
def p(name): return root / name
def read(name): return p(name).read_text(encoding='utf-8')
def write(name, s): p(name).write_text(s, encoding='utf-8')

# 1) Giao diện: bỏ nhập mã phòng với user, hiển thị danh sách phòng.
s = read('index.html')
old = '''          <div id="mp-panel" class="mp-panel">
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
          </div>'''
new = '''          <div id="mp-panel" class="mp-panel">
            <div class="mp-title">👥 Phòng chơi</div>
            <div id="mp-status" class="mp-status">Đang kiểm tra tài khoản…</div>
            <div id="mp-admin-actions" class="mp-admin-actions" hidden>
              <button id="mp-create-room" type="button">➕ Tạo phòng mới</button>
            </div>
            <div id="mp-room-list-wrap" class="mp-room-list-wrap">
              <div class="mp-list-title">Danh sách phòng đang có</div>
              <div id="mp-room-list" class="mp-room-list"><div class="mp-empty">Đang tải danh sách phòng…</div></div>
              <button id="mp-refresh-rooms" type="button" class="mp-refresh">↻ Làm mới danh sách</button>
            </div>
            <div id="mp-current" class="mp-current" hidden>
              <div>Phòng: <b id="mp-current-code">—</b> · <span id="mp-count">1 người</span></div>
              <div id="mp-player-list" class="mp-player-list"></div>
              <button id="mp-leave-room" type="button" class="mp-leave">Rời phòng</button>
            </div>
          </div>'''
if old not in s:
    raise RuntimeError('Không tìm thấy khối giao diện phòng chơi để thay')
s = s.replace(old, new)
write('index.html', s)

# 2) Logic: chỉ admin được tạo phòng, user chọn phòng từ danh sách.
s = read('src/multiplayer.ts')
s = s.replace('  private joined = false;\n', '  private joined = false;\n  private isAdmin = false;\n')

s = s.replace("      .select('display_name')", ".select('display_name')")
s = s.replace("    this.displayName = String(profile?.display_name || 'Người chơi');\n    this.setStatus('Xin chào ' + this.displayName + '. Tạo phòng mới hoặc nhập mã phòng của bạn bè.');\n    this.setActionsEnabled(true);\n    this.createHud();",
'''    this.displayName = String(profile?.display_name || 'Người chơi');
    const { data: adminRow } = await this.supabase
      .from('game_admins')
      .select('user_id')
      .eq('user_id', user.id)
      .maybeSingle();
    this.isAdmin = Boolean(adminRow);
    const adminActions = document.querySelector<HTMLElement>('#mp-admin-actions');
    if (adminActions) adminActions.hidden = !this.isAdmin;
    this.setStatus(this.isAdmin
      ? 'Bạn đang dùng quyền quản trị. Có thể tạo phòng mới và vào các phòng đang có.'
      : 'Chọn một phòng trong danh sách để vào chơi cùng mọi người.');
    this.createHud();
    await this.loadRoomList();''')

# Bind UI mới
start = s.index('  private bindUi(): void {')
end = s.index('  private setActionsEnabled', start)
new_bind = '''  private bindUi(): void {
    document.querySelector<HTMLButtonElement>('#mp-create-room')?.addEventListener('click', () => void this.createRoom());
    document.querySelector<HTMLButtonElement>('#mp-refresh-rooms')?.addEventListener('click', () => void this.loadRoomList());
    document.querySelector<HTMLButtonElement>('#mp-leave-room')?.addEventListener('click', () => void this.leaveRoom());
    document.querySelector<HTMLElement>('#mp-room-list')?.addEventListener('click', (event) => {
      const target = event.target as HTMLElement;
      const button = target.closest<HTMLButtonElement>('button[data-room-code]');
      if (!button) return;
      void this.joinRoomByCode(button.dataset.roomCode || '');
    });
  }

'''
s = s[:start] + new_bind + s[end:]

# setActionsEnabled không còn input/code; giữ an toàn cho create button.
start = s.index('  private setActionsEnabled(enabled: boolean): void {')
end = s.index('  private setStatus', start)
s = s[:start] + '''  private setActionsEnabled(enabled: boolean): void {
    const create = document.querySelector<HTMLButtonElement>('#mp-create-room');
    if (create) create.disabled = !enabled || !this.isAdmin;
  }

''' + s[end:]

# Thêm loadRoomList trước createRoom
marker = '  async createRoom(): Promise<void> {'
method = '''  private async loadRoomList(): Promise<void> {
    const list = document.querySelector<HTMLElement>('#mp-room-list');
    if (!list) return;
    list.innerHTML = '<div class="mp-empty">Đang tải danh sách phòng…</div>';
    const { data, error } = await this.supabase
      .from('game_rooms')
      .select('id,code,name,world_seed,max_players,created_at')
      .order('created_at', { ascending: false })
      .limit(30);
    if (error) {
      list.innerHTML = '<div class="mp-empty">Không tải được danh sách phòng.</div>';
      return;
    }
    const rooms = data || [];
    if (!rooms.length) {
      list.innerHTML = this.isAdmin
        ? '<div class="mp-empty">Chưa có phòng nào. Hãy tạo phòng đầu tiên.</div>'
        : '<div class="mp-empty">Hiện chưa có phòng chơi. Vui lòng chờ quản trị viên tạo phòng.</div>';
      return;
    }
    list.innerHTML = rooms.map((room) => {
      const name = String(room.name || ('Phòng ' + room.code));
      const code = String(room.code || '');
      return '<div class="mp-room-card">'
        + '<div><div class="mp-room-name">🏠 ' + this.escapeHtml(name) + '</div>'
        + '<div class="mp-room-code">Mã: ' + this.escapeHtml(code) + '</div></div>'
        + '<button type="button" data-room-code="' + this.escapeHtml(code) + '">Vào chơi</button>'
        + '</div>';
    }).join('');
  }

  private escapeHtml(value: string): string {
    return value.replace(/[&<>"']/g, (ch) => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    }[ch] || ch));
  }

'''
s = s.replace(marker, method + marker)

# Chặn tạo phòng ở client nữa.
s = s.replace("  async createRoom(): Promise<void> {\n    if (!this.userId) return;",
'''  async createRoom(): Promise<void> {
    if (!this.userId) return;
    if (!this.isAdmin) {
      this.setStatus('Chỉ quản trị viên mới được tạo phòng.', true);
      return;
    }''')

# Sau khi tạo/join/leave thì làm mới danh sách.
s = s.replace('        await this.joinRoom(data as RoomRow);\n        return;', '        await this.joinRoom(data as RoomRow);\n        await this.loadRoomList();\n        return;')
s = s.replace("      this.setStatus('Đã rời phòng. Bạn có thể tạo hoặc vào phòng khác.');", "      this.setStatus('Đã rời phòng. Chọn phòng khác trong danh sách để tiếp tục.');\n      void this.loadRoomList();")

write('src/multiplayer.ts', s)

# 3) CSS danh sách phòng
s = read('src/style.css')
s += r'''
/* ===== Danh sách phòng do quản trị viên tạo ===== */
.mp-admin-actions{margin-top:10px}.mp-admin-actions button{width:100%;border:0;border-radius:12px;padding:11px 12px;background:#ffd166;color:#4b3500;font-weight:900}
.mp-room-list-wrap{margin-top:11px}.mp-list-title{font-weight:900;font-size:13px;margin-bottom:7px;color:#fff}.mp-room-list{display:grid;gap:7px;max-height:220px;overflow:auto;padding-right:2px}
.mp-room-card{display:grid;grid-template-columns:1fr auto;gap:10px;align-items:center;background:rgba(255,255,255,.1);border:1px solid rgba(255,255,255,.15);border-radius:13px;padding:9px 10px;text-align:left}
.mp-room-name{font-size:13px;font-weight:900;color:#fff}.mp-room-code{font-size:10px;color:#cfe7ff;margin-top:3px}.mp-room-card button,.mp-refresh{border:0;border-radius:10px;padding:9px 11px;font-weight:900;background:#dff7ff;color:#123c56}
.mp-refresh{width:100%;margin-top:8px;background:rgba(255,255,255,.13);color:#fff;border:1px solid rgba(255,255,255,.18)}.mp-empty{font-size:12px;color:#d6e8f5;padding:10px;text-align:center;background:rgba(255,255,255,.06);border-radius:11px}
@media(pointer:coarse){.mp-room-card button{min-height:44px;min-width:92px}}
'''
write('src/style.css', s)

print('Đã chuyển Block World sang mô hình admin tạo phòng, user chọn phòng từ danh sách.')