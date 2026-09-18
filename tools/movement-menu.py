from pathlib import Path
import sys

root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('.')
def p(name): return root / name
def read(name): return p(name).read_text(encoding='utf-8')
def write(name,s): p(name).write_text(s,encoding='utf-8')

# 1) Controller: thêm về điểm bắt đầu riêng biệt.
s = read('src/player/controller.ts')
if 'private homePosition' not in s:
    s = s.replace(
        '  private safePosition: { x: number; y: number; z: number };\n',
        '  private safePosition: { x: number; y: number; z: number };\n'
        '  private homePosition: { x: number; y: number; z: number };\n'
    )
    s = s.replace(
        '    this.safePosition = { x: spawnX, y: groundY, z: spawnZ };\n',
        '    this.safePosition = { x: spawnX, y: groundY, z: spawnZ };\n'
        '    this.homePosition = { x: spawnX, y: groundY, z: spawnZ };\n'
    )

if 'goHome(): void' not in s:
    needle = '  rescue(): void {\n'
    insert = '''  goHome(): void {\n    this.state = {\n      position: { ...this.homePosition },\n      velocity: { x: 0, y: 0, z: 0 },\n      onGround: false,\n    };\n    this.safePosition = { ...this.homePosition };\n    this.syncCamera();\n    window.dispatchEvent(new CustomEvent('blockworld-home'));\n  }\n\n  rescue(): void {\n'''
    if needle not in s:
        raise SystemExit('Không tìm thấy rescue() để chèn goHome()')
    s = s.replace(needle, insert, 1)
write('src/player/controller.ts', s)

# 2) Main UI: chỉ giữ 1 nút DI CHUYỂN, panel có CỨU và ĐI TỚI.
s = read('src/main.ts')

# Đổi nút command thành nút di chuyển chung.
s = s.replace("commandButton.id = 'blockworld-command-button';", "commandButton.id = 'blockworld-move-button';")
s = s.replace("commandButton.textContent = '⌨ ĐI TỚI';", "commandButton.textContent = '🧭 DI CHUYỂN';")
s = s.replace("commandButton.setAttribute('aria-label', 'Dịch chuyển nhanh đến tọa độ');", "commandButton.setAttribute('aria-label', 'Mở bảng di chuyển');")

old_panel = '''  commandPanel.innerHTML = `\n    <div class="bw-command-card">\n      <div class="bw-command-title">🚀 Dịch chuyển nhanh</div>\n      <div class="bw-command-help">Nhập <b>X Z</b> để tự tìm mặt đất, hoặc <b>X Y Z</b> để đến đúng độ cao.<br>Ví dụ: <code>120 -45</code> hoặc <code>/tp 120 35 -45</code></div>\n      <input id="bw-command-input" inputmode="text" autocomplete="off" placeholder="Ví dụ: 120 -45" />\n      <div class="bw-command-actions">\n        <button id="bw-command-go" type="button">🚀 ĐI TỚI</button>\n        <button id="bw-command-close" type="button">ĐÓNG</button>\n      </div>\n      <div id="bw-command-message"></div>\n    </div>`;\n'''
new_panel = '''  commandPanel.innerHTML = `\n    <div class="bw-command-card">\n      <div class="bw-command-title">🧭 Di chuyển</div>\n\n      <div class="bw-move-section bw-rescue-section">\n        <div class="bw-section-title">🛟 Cứu</div>\n        <div class="bw-command-help">Đưa nhân vật về đúng nơi bắt đầu của thế giới.</div>\n        <button id="bw-command-rescue" class="bw-full-button bw-rescue-button" type="button">🛟 CỨU · VỀ NƠI BẮT ĐẦU</button>\n      </div>\n\n      <div class="bw-move-divider"></div>\n\n      <div class="bw-move-section">\n        <div class="bw-section-title">🚀 Đi tới tọa độ</div>\n        <div class="bw-command-help">Nhập <b>X Z</b> để tự tìm mặt đất, hoặc <b>X Y Z</b> để đến đúng độ cao.<br>Ví dụ: <code>120 -45</code> hoặc <code>/tp 120 35 -45</code></div>\n        <input id="bw-command-input" inputmode="text" autocomplete="off" placeholder="Ví dụ: 120 -45" />\n        <button id="bw-command-go" class="bw-full-button bw-go-button" type="button">🚀 ĐI TỚI</button>\n        <div id="bw-command-message"></div>\n      </div>\n\n      <button id="bw-command-close" class="bw-close-button" type="button">ĐÓNG</button>\n    </div>`;\n'''
if old_panel in s:
    s = s.replace(old_panel, new_panel)
elif 'bw-command-rescue' not in s:
    raise SystemExit('Không tìm thấy khối commandPanel để thay giao diện')

# Thêm listener nút cứu trong panel.
needle = "  const cmdMessage = commandPanel.querySelector<HTMLElement>('#bw-command-message')!;\n"
if needle in s and "#bw-command-rescue" not in s.split(needle,1)[1][:1200]:
    add = needle + "  commandPanel.querySelector<HTMLButtonElement>('#bw-command-rescue')!.addEventListener('click', () => { player.goHome(); commandPanel.classList.remove('show'); });\n"
    s = s.replace(needle, add, 1)

# Toast khi về nơi bắt đầu.
if 'blockworld-home-toast' not in s:
    needle2 = "  window.addEventListener('blockworld-teleported', ((event: Event) => {\n"
    home_toast = '''  const homeToast = document.createElement('div');\n  homeToast.id = 'blockworld-home-toast';\n  homeToast.textContent = '🛟 Đã về nơi bắt đầu';\n  document.body.appendChild(homeToast);\n  window.addEventListener('blockworld-home', () => {\n    homeToast.classList.add('show');\n    window.setTimeout(() => homeToast.classList.remove('show'), 1500);\n  });\n\n'''
    if needle2 not in s:
        raise SystemExit('Không tìm thấy teleport listener để chèn home toast')
    s = s.replace(needle2, home_toast + needle2, 1)
write('src/main.ts', s)

# 3) CSS: ẩn nút cứu cũ, đổi nút command thành DI CHUYỂN và bố trí panel 2 khu vực.
s = read('src/style.css')
if '/* ===== Menu di chuyển hợp nhất ===== */' not in s:
    s += r'''

/* ===== Menu di chuyển hợp nhất ===== */
#blockworld-rescue-button{display:none!important}
#blockworld-command-button{display:none!important}
#blockworld-move-button{
  position:fixed;z-index:27;right:max(10px,env(safe-area-inset-right));
  top:max(96px,calc(env(safe-area-inset-top) + 90px));
  border:2px solid rgba(255,255,255,.78);border-radius:999px;
  padding:10px 13px;background:rgba(37,99,235,.92);color:#fff;
  font:900 12px Arial,sans-serif;box-shadow:0 4px 14px rgba(0,0,0,.35);
  touch-action:manipulation;-webkit-tap-highlight-color:transparent
}
#blockworld-move-button:active{transform:scale(.96)}
.bw-move-section{padding:12px;border-radius:14px;background:rgba(255,255,255,.055)}
.bw-rescue-section{background:rgba(14,116,144,.18)}
.bw-section-title{font:900 16px Arial,sans-serif;margin-bottom:6px}
.bw-move-divider{height:1px;background:rgba(255,255,255,.18);margin:12px 0}
.bw-full-button{width:100%;min-height:46px;border:0;border-radius:12px;font:900 14px Arial,sans-serif;margin-top:8px}
.bw-rescue-button{background:#0e7490;color:#fff}
.bw-go-button{background:#4f46e5;color:#fff}
.bw-close-button{width:100%;min-height:42px;margin-top:12px;border:0;border-radius:12px;background:#dbeafe;color:#17324d;font:900 13px Arial,sans-serif}
#blockworld-home-toast{position:fixed;z-index:110;left:50%;top:20%;transform:translate(-50%,-10px);opacity:0;pointer-events:none;padding:10px 14px;border-radius:999px;background:rgba(14,116,144,.95);color:#fff;font:900 13px Arial,sans-serif;transition:.2s;white-space:nowrap}
#blockworld-home-toast.show{opacity:1;transform:translate(-50%,0)}
@media(pointer:coarse),(max-width:768px){
  #blockworld-move-button{top:max(96px,calc(env(safe-area-inset-top) + 90px));right:max(10px,env(safe-area-inset-right));font-size:11px;padding:9px 11px}
  .bw-command-card{max-height:88vh;overflow:auto}
}
@media(pointer:fine){#blockworld-move-button{top:58px}}
'''
write('src/style.css', s)

print('Đã gộp CỨU và ĐI TỚI vào một nút DI CHUYỂN.')
