from pathlib import Path
import sys

root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('.')
def p(name): return root / name
def read(name): return p(name).read_text(encoding='utf-8')
def write(name,s): p(name).write_text(s,encoding='utf-8')

# 1) Ổn định vật lý: giảm bước thời gian và tránh vòng lặp tự cứu liên tục.
s = read('src/player/controller.ts')
if 'const safeDt = Math.min(dt, 0.04);' not in s:
    s = s.replace('  update(dt: number): void {\n    if (this.controlMode !== "idle") {', '  update(dt: number): void {\n    const safeDt = Math.min(dt, 0.04);\n    if (this.controlMode !== "idle") {', 1)
    s = s.replace('        dt,\n        (x, y, z) => isSolid(this.world.getBlock(x, y, z)),', '        safeDt,\n        (x, y, z) => isSolid(this.world.getBlock(x, y, z)),', 1)
    s = s.replace('      this.safeCheckTimer += dt;', '      this.safeCheckTimer += safeDt;')

old_auto = '''      // Rơi xuống hố sâu thì tự đưa về điểm an toàn gần nhất.\n      if (this.state.position.y < this.safePosition.y - 9 || this.state.position.y < 2) {\n        this.rescue();\n      }\n'''
new_auto = '''      // Chỉ tự đưa về nhà khi thật sự rơi ra khỏi thế giới.\n      // Không tự cứu theo chênh lệch độ cao để tránh vòng lặp rơi-cứu-rơi trên máy chậm.\n      if (this.state.position.y < -12 && performance.now() - this.lastRescueAt > 2500) {\n        this.goHome();\n        this.lastRescueAt = performance.now();\n      }\n'''
if old_auto in s:
    s = s.replace(old_auto, new_auto)

# goHome luôn tính lại mặt đất tại điểm bắt đầu, phòng trường hợp dữ liệu địa hình vừa tải lại.
old_home = '''  goHome(): void {\n    this.state = {\n      position: { ...this.homePosition },\n      velocity: { x: 0, y: 0, z: 0 },\n      onGround: false,\n    };\n    this.safePosition = { ...this.homePosition };\n    this.syncCamera();\n    window.dispatchEvent(new CustomEvent('blockworld-home'));\n  }\n'''
new_home = '''  goHome(): void {\n    const hx = this.homePosition.x;\n    const hz = this.homePosition.z;\n    const hy = findGroundHeight(\n      Math.floor(hx),\n      Math.floor(hz),\n      CHUNK_HEIGHT - 1,\n      (x, y, z) => isSolid(this.world.getBlock(x, y, z)),\n    );\n    const home = { x: hx, y: Math.max(2, hy), z: hz };\n    this.homePosition = { ...home };\n    this.safePosition = { ...home };\n    this.state = {\n      position: { ...home },\n      velocity: { x: 0, y: 0, z: 0 },\n      onGround: false,\n    };\n    this.syncCamera();\n    window.dispatchEvent(new CustomEvent('blockworld-home'));\n  }\n'''
if old_home in s:
    s = s.replace(old_home, new_home)
write('src/player/controller.ts', s)

# 2) Giảm tải thế giới trên điện thoại / máy yếu.
s = read('src/main.ts')
if 'const IS_MOBILE_GAME' not in s:
    s = s.replace('const DEFAULT_SEED = 2026;\n', 'const DEFAULT_SEED = 2026;\nconst IS_MOBILE_GAME = window.matchMedia("(pointer: coarse)").matches || window.innerWidth <= 768;\n')
s = s.replace('const STREAM_RADIUS_WEBGL = 9;', 'const STREAM_RADIUS_WEBGL = IS_MOBILE_GAME ? 5 : 8;')
s = s.replace('const STREAM_RADIUS_CPU = 4;', 'const STREAM_RADIUS_CPU = IS_MOBILE_GAME ? 3 : 4;')
s = s.replace('const MESH_BUDGET_PER_FRAME = 3;', 'const MESH_BUDGET_PER_FRAME = IS_MOBILE_GAME ? 1 : 3;')
write('src/main.ts', s)

# 3) Giảm độ phân giải render trên mobile để giữ FPS ổn định.
s = read('src/render/scene.ts')
if 'const MOBILE_RENDER' not in s:
    s = s.replace('export const SKY_COLOR = 0x87ceeb;\n', 'export const SKY_COLOR = 0x87ceeb;\nconst MOBILE_RENDER = window.matchMedia("(pointer: coarse)").matches || window.innerWidth <= 768;\n')
s = s.replace('    antialias: true,', '    antialias: !MOBILE_RENDER,')
s = s.replace('  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));', '  renderer.setPixelRatio(Math.min(window.devicePixelRatio, MOBILE_RENDER ? 1.15 : 1.75));')
s = s.replace('  const basePixelRatio = Math.min(window.devicePixelRatio, 2);', '  const basePixelRatio = Math.min(window.devicePixelRatio, MOBILE_RENDER ? 1.15 : 1.75);')
write('src/render/scene.ts', s)

# 4) Khóa viewport game đúng kích thước màn hình thực tế trên mobile.
s = read('src/style.css')
marker = '/* ===== Ổn định mobile / màn hình nhỏ ===== */'
if marker not in s:
    s += r'''

/* ===== Ổn định mobile / màn hình nhỏ ===== */
html,body,#app{width:100%;height:100%;height:100dvh;max-width:100vw;overflow:hidden;overscroll-behavior:none}
body{touch-action:none;-webkit-text-size-adjust:100%}
canvas{display:block;width:100vw!important;height:100dvh!important;max-width:100vw;max-height:100dvh}
@media (pointer:coarse),(max-width:768px){
  #overlay-content{width:min(92vw,430px);max-height:82dvh;overflow:auto;padding:16px!important}
  #hotbar{max-width:94vw;overflow-x:auto;overflow-y:hidden;scrollbar-width:none}
  #hotbar::-webkit-scrollbar{display:none}
  .touch-buttons{transform:scale(.92);transform-origin:right bottom}
  #blockworld-move-button{max-width:38vw;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
  .bw-command-card{width:min(94vw,430px)!important;max-height:84dvh!important;overflow:auto!important;padding:14px!important}
}
@media (max-height:620px) and (orientation:landscape){
  #fps{top:8px!important;left:74px!important;font-size:10px!important}
  #blockworld-move-button{top:8px!important;right:8px!important}
  .touch-buttons{bottom:8px!important;transform:scale(.8)}
}
'''
write('src/style.css', s)
print('Đã ổn định vật lý, giảm tải và tối ưu màn hình Block World.')