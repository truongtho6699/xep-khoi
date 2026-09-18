from pathlib import Path
import sys

root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('.')
def p(name): return root / name
def read(name): return p(name).read_text(encoding='utf-8')
def write(name,s): p(name).write_text(s,encoding='utf-8')

# 1) PlayerController: thêm dịch chuyển an toàn.
s = read('src/player/controller.ts')
if 'teleportTo(' not in s:
    needle = '''  rescue(): void {\n    const now = performance.now();'''
    insert = '''  teleportTo(x: number, y: number | null, z: number): boolean {\n    if (!Number.isFinite(x) || !Number.isFinite(z) || (y !== null && !Number.isFinite(y))) return false;\n    let targetY = y;\n    if (targetY === null) {\n      targetY = findGroundHeight(\n        Math.floor(x),\n        Math.floor(z),\n        CHUNK_HEIGHT - 1,\n        (xx, yy, zz) => isSolid(this.world.getBlock(xx, yy, zz)),\n      );\n    }\n    targetY = Math.max(2, Math.min(CHUNK_HEIGHT - 3, targetY));\n    const tx = Math.round(x * 100) / 100;\n    const tz = Math.round(z * 100) / 100;\n    this.state = {\n      position: { x: tx, y: targetY, z: tz },\n      velocity: { x: 0, y: 0, z: 0 },\n      onGround: false,\n    };\n    this.safePosition = { x: tx, y: targetY, z: tz };\n    this.syncCamera();\n    window.dispatchEvent(new CustomEvent('blockworld-teleported', { detail: { x: tx, y: targetY, z: tz } }));\n    return true;\n  }\n\n  rescue(): void {\n    const now = performance.now();'''
    if needle not in s:
        raise SystemExit('Không tìm thấy rescue() để chèn teleportTo')
    s = s.replace(needle, insert)
write('src/player/controller.ts', s)

# 2) Giao diện lệnh dịch chuyển.
s = read('src/main.ts')
if 'blockworld-command-button' not in s:
    needle = "  document.body.appendChild(rescueButton);\n"
    insert = '''  document.body.appendChild(rescueButton);\n\n  const commandButton = document.createElement('button');\n  commandButton.id = 'blockworld-command-button';\n  commandButton.type = 'button';\n  commandButton.textContent = '⌨ ĐI TỚI';\n  commandButton.setAttribute('aria-label', 'Dịch chuyển nhanh đến tọa độ');\n  document.body.appendChild(commandButton);\n\n  const commandPanel = document.createElement('div');\n  commandPanel.id = 'blockworld-command-panel';\n  commandPanel.innerHTML = `\n    <div class="bw-command-card">\n      <div class="bw-command-title">🚀 Dịch chuyển nhanh</div>\n      <div class="bw-command-help">Nhập <b>X Z</b> để tự tìm mặt đất, hoặc <b>X Y Z</b> để đến đúng độ cao.<br>Ví dụ: <code>120 -45</code> hoặc <code>/tp 120 35 -45</code></div>\n      <input id="bw-command-input" inputmode="text" autocomplete="off" placeholder="Ví dụ: 120 -45" />\n      <div class="bw-command-actions">\n        <button id="bw-command-go" type="button">🚀 ĐI TỚI</button>\n        <button id="bw-command-close" type="button">ĐÓNG</button>\n      </div>\n      <div id="bw-command-message"></div>\n    </div>`;\n  document.body.appendChild(commandPanel);\n\n  const cmdInput = commandPanel.querySelector<HTMLInputElement>('#bw-command-input')!;\n  const cmdMessage = commandPanel.querySelector<HTMLElement>('#bw-command-message')!;\n  const closePanel = () => commandPanel.classList.remove('show');\n  commandButton.addEventListener('click', (e) => {\n    e.preventDefault(); e.stopPropagation();\n    const p = player.position;\n    cmdInput.value = `${Math.floor(p.x)} ${Math.floor(p.z)}`;\n    cmdMessage.textContent = '';\n    commandPanel.classList.add('show');\n    window.setTimeout(() => { cmdInput.focus(); cmdInput.select(); }, 30);\n  });\n  commandPanel.querySelector<HTMLButtonElement>('#bw-command-close')!.addEventListener('click', closePanel);\n  commandPanel.addEventListener('click', (e) => { if (e.target === commandPanel) closePanel(); });\n\n  const runTeleportCommand = () => {\n    const raw = cmdInput.value.trim().replace(/^\\/?tp\\s+/i, '');\n    const parts = raw.split(/[\\s,;]+/).filter(Boolean).map(Number);\n    let ok = false;\n    if (parts.length === 2) ok = player.teleportTo(parts[0], null, parts[1]);\n    else if (parts.length === 3) ok = player.teleportTo(parts[0], parts[1], parts[2]);\n    if (!ok) {\n      cmdMessage.textContent = '⚠️ Hãy nhập X Z hoặc X Y Z. Ví dụ: 120 -45';\n      return;\n    }\n    closePanel();\n  };\n  commandPanel.querySelector<HTMLButtonElement>('#bw-command-go')!.addEventListener('click', runTeleportCommand);\n  cmdInput.addEventListener('keydown', (e) => { if (e.key === 'Enter') runTeleportCommand(); });\n\n  const teleportToast = document.createElement('div');\n  teleportToast.id = 'blockworld-teleport-toast';\n  document.body.appendChild(teleportToast);\n  window.addEventListener('blockworld-teleported', ((event: Event) => {\n    const d = (event as CustomEvent<{x:number;y:number;z:number}>).detail;\n    teleportToast.textContent = `🚀 Đã đến X ${Math.floor(d.x)} · Y ${Math.floor(d.y)} · Z ${Math.floor(d.z)}`;\n    teleportToast.classList.add('show');\n    window.setTimeout(() => teleportToast.classList.remove('show'), 1600);\n  }) as EventListener);\n'''
    if needle not in s:
        raise SystemExit('Không tìm thấy vị trí chèn command UI')
    s = s.replace(needle, insert)
write('src/main.ts', s)

# 3) CSS mobile/desktop.
s = read('src/style.css')
if '#blockworld-command-button' not in s:
    s += r'''

/* ===== Lệnh dịch chuyển nhanh ===== */
#blockworld-command-button{
  position:fixed;z-index:25;right:max(14px,env(safe-area-inset-right));top:max(78px,calc(env(safe-area-inset-top) + 70px));
  border:2px solid rgba(255,255,255,.72);border-radius:999px;padding:10px 13px;
  background:rgba(94,53,177,.9);color:#fff;font:900 12px Arial,sans-serif;
  box-shadow:0 4px 14px rgba(0,0,0,.32);touch-action:manipulation;-webkit-tap-highlight-color:transparent
}
#blockworld-command-panel{position:fixed;z-index:100;inset:0;display:none;align-items:center;justify-content:center;padding:16px;background:rgba(0,0,0,.62)}
#blockworld-command-panel.show{display:flex}
.bw-command-card{width:min(92vw,430px);border:1px solid rgba(255,255,255,.25);border-radius:20px;padding:18px;background:#102b3d;color:#fff;box-shadow:0 12px 40px #0008;font-family:Arial,sans-serif}
.bw-command-title{font-size:20px;font-weight:900;margin-bottom:8px}.bw-command-help{font-size:13px;line-height:1.55;color:#d9edff;margin-bottom:12px}.bw-command-help code{background:#071b28;padding:2px 5px;border-radius:5px;color:#fff}
#bw-command-input{width:100%;height:48px;border:2px solid #7dd3fc;border-radius:12px;padding:0 12px;font:800 17px monospace;background:#fff;color:#111;outline:none}
.bw-command-actions{display:grid;grid-template-columns:1fr .7fr;gap:9px;margin-top:10px}.bw-command-actions button{min-height:46px;border:0;border-radius:12px;font-weight:900;font-size:14px}.bw-command-actions button:first-child{background:#4f46e5;color:#fff}.bw-command-actions button:last-child{background:#dbeafe;color:#17324d}
#bw-command-message{min-height:20px;margin-top:8px;font-size:12px;color:#ffd8a8}
#blockworld-teleport-toast{position:fixed;z-index:110;left:50%;top:20%;transform:translate(-50%,-10px);opacity:0;pointer-events:none;padding:10px 14px;border-radius:999px;background:rgba(68,36,140,.94);color:#fff;font:900 13px Arial,sans-serif;transition:.2s;white-space:nowrap;max-width:92vw;overflow:hidden;text-overflow:ellipsis}
#blockworld-teleport-toast.show{opacity:1;transform:translate(-50%,0)}
@media(pointer:coarse){
  #blockworld-command-button{top:max(112px,calc(env(safe-area-inset-top) + 104px));right:max(10px,env(safe-area-inset-right));font-size:11px;padding:9px 11px}
}
@media(pointer:fine){#blockworld-command-button{top:58px}}
'''
write('src/style.css', s)
print('Đã thêm lệnh /tp và nút ĐI TỚI theo tọa độ.')
