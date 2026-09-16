from pathlib import Path
import re
import sys

root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
def p(name): return root / name
def read(name): return p(name).read_text(encoding="utf-8")
def write(name, s): p(name).write_text(s, encoding="utf-8")

# 1) GitHub Pages base path
s = read("vite.config.ts")
s = re.sub(r'base:\s*process\.env\.GITHUB_PAGES\s*\?\s*"/minecraft-clone/"\s*:\s*"/",',
           'base: "/xep-khoi/minecraft/",', s)
write("vite.config.ts", s)

# 2) Full Vietnamese launch screen
write("index.html", """<!doctype html>
<html lang="vi">
  <head>
    <meta charset="UTF-8" />
    <link rel="icon" type="image/svg+xml" href="/favicon.svg" />
    <meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no,viewport-fit=cover" />
    <meta name="mobile-web-app-capable" content="yes" />
    <meta name="apple-mobile-web-app-capable" content="yes" />
    <meta name="apple-mobile-web-app-title" content="Block World – Game Cá Voi" />
    <meta name="theme-color" content="#87ceeb" />
    <meta name="description" content="Block World – Game Cá Voi: thế giới khối 3D vui nhộn dành cho trẻ em." />
    <title>Block World – Game Cá Voi</title>
  </head>
  <body>
    <div id="app">
      <div id="crosshair" aria-hidden="true"></div>
      <div id="hotbar"></div>
      <div id="overlay">
        <div id="overlay-content">
          <h1>🐳 Block World</h1>
          <h2>Game Cá Voi</h2>
          <p class="controls-desktop">
            <b>Di chuyển:</b> W A S D · <b>Nhìn:</b> chuột · <b>Nhảy:</b> phím cách<br />
            <b>Phá khối:</b> chuột trái · <b>Đặt khối:</b> chuột phải<br />
            <b>Chọn khối:</b> phím 1–7 hoặc cuộn chuột
          </p>
          <p class="controls-touch">
            👈 <b>Bên trái:</b> kéo để di chuyển<br />
            👉 <b>Bên phải:</b> vuốt để xoay hướng nhìn<br />
            Dùng các nút lớn <b>PHÁ · ĐẶT · NHẢY</b><br />
            Chạm ô vật liệu phía dưới để chọn khối
          </p>
          <button id="play-button" type="button">▶ BẮT ĐẦU CHƠI</button>
          <p class="kid-note">Chơi vui nhé! 🐳</p>
        </div>
      </div>
    </div>
    <script type="module" src="/src/main.ts"></script>
  </body>
</html>
""")

# 3) User-visible errors and quality labels
s = read("src/main.ts")
s = s.replace('const message = error instanceof Error ? error.message : String(error);',
              'const message = "Trò chơi gặp lỗi khi khởi động. Hãy tải lại trang hoặc mở bằng Chrome/Safari.";')
s = s.replace('title.textContent = "the game couldn\'t start";',
              'title.textContent = "Không thể khởi động trò chơi";')
s = re.sub(r'hint\.textContent\s*=\s*"Try a hard refresh[\s\S]*?message\.";',
           'hint.textContent = "Nếu vẫn chưa vào được, hãy đóng trò chơi rồi mở lại.";', s)
s = re.sub(r'qualityNote:\s*\(\)\s*=>\s*[^,]+scale[^,]+,',
           'qualityNote: () => Math.round(gameScene.pixelRatio() * 100).toString() + "% độ phân giải",', s)
s = re.sub(r'qualityNote:\s*\(\)\s*=>\s*[^,]+cpu[^,]+,',
           'qualityNote: () => "chế độ nhẹ " + cpu.internalWidth.toString() + "p",', s)
write("src/main.ts", s)

# 4) Vietnamese HUD
s = read("src/ui/hud.ts")
s = re.sub(
    r'this\.el\.textContent\s*=\s*\x60[^\x60]+\x60;',
    'this.el.textContent = fps.toString() + " hình/giây · vị trí (" + pos + ") · " + info.chunks.toString() + " vùng · mã thế giới " + info.seed.toString() + note;',
    s,
)
write("src/ui/hud.ts", s)

# 5) Vietnamese block names
s = read("src/world/blocks.ts")
for a, b in {
    '"air"':'"không khí"', '"grass"':'"cỏ"', '"dirt"':'"đất"', '"stone"':'"đá"',
    '"sand"':'"cát"', '"water"':'"nước"', '"wood"':'"gỗ"', '"leaves"':'"lá cây"',
    '"bedrock"':'"đá nền"', '"snow"':'"tuyết"'
}.items():
    s = s.replace(a, b)
write("src/world/blocks.ts", s)

# 6) Hotbar accessibility/tooltips in Vietnamese
s = read("src/ui/hotbar.ts")
s = s.replace('import { BlockId, PLACEABLE_BLOCKS } from "../world/blocks";',
              'import { BlockId, BLOCKS, PLACEABLE_BLOCKS } from "../world/blocks";')
s = s.replace('slot.className = "hotbar-slot";',
              'slot.className = "hotbar-slot";\n      slot.title = "Khối " + BLOCKS[blockId].name;\n      slot.setAttribute("aria-label", "Chọn khối " + BLOCKS[blockId].name);')
write("src/ui/hotbar.ts", s)

# 7) Three large kid-friendly touch buttons
s = read("src/ui/touch-controls.ts")
pattern = r'this\.buttons\.append\([\s\S]*?\n\s*\);\n\n\s*root\.append'
replacement = '''this.buttons.append(
      this.makeButton("touch-break", "⛏ PHÁ", {
        press: () => {
          if (this.handlers.isActive()) this.handlers.onBreak();
        },
      }),
      this.makeButton("touch-place", "▣ ĐẶT", {
        press: () => {
          if (this.handlers.isActive()) this.handlers.onPlace();
        },
      }),
      this.makeButton("touch-jump", "⬆ NHẢY", {
        press: () => {
          this.jumpHeld = true;
          this.emit();
        },
        release: () => {
          this.jumpHeld = false;
          this.emit();
        },
      }),
    );

    root.append'''
s, n = re.subn(pattern, replacement, s, count=1)
if n != 1:
    raise RuntimeError("Không sửa được cụm nút cảm ứng")
s = s.replace('el.textContent = label;',
              'el.textContent = label;\n    el.setAttribute("aria-label", label);')
write("src/ui/touch-controls.ts", s)

# 8) Kid/mobile CSS
s = read("src/style.css")
s += """
/* ===== Block World – Game Cá Voi ===== */
#overlay-content{width:min(92vw,620px);padding:22px 18px;border-radius:24px;background:rgba(10,30,48,.82);box-shadow:0 14px 44px rgba(0,0,0,.38)}
#overlay-content h1{margin:0;font-size:clamp(2rem,8vw,3.25rem);color:#c9efff;text-shadow:0 3px 0 rgba(0,0,0,.28)}
#overlay-content h2{margin:3px 0 14px;font-size:clamp(1.1rem,4.5vw,1.55rem)}
#overlay-content p{line-height:1.65;font-size:15px}
.kid-note{font-weight:800;color:#bfe9ff}
#play-button{min-width:220px;min-height:60px;border-radius:18px;padding:14px 24px;font-size:18px;font-weight:900;box-shadow:0 5px 0 #2e7d32}
#play-button:active{transform:translateY(3px);box-shadow:0 2px 0 #2e7d32}
.touch-buttons{gap:9px;align-items:flex-end}
.touch-button{width:86px;height:66px;border-radius:18px;font-size:15px;font-weight:900;background:rgba(8,25,42,.76);border:3px solid rgba(255,255,255,.78);box-shadow:0 4px 12px rgba(0,0,0,.38);text-shadow:0 1px 2px #000}
.touch-break{background:rgba(194,55,43,.86)}
.touch-place{background:rgba(29,126,72,.88)}
.touch-jump{background:rgba(35,91,184,.88)}
.touch-stick-base{width:150px;height:150px;margin:-75px 0 0 -75px;background:rgba(40,110,160,.25);border:4px solid rgba(255,255,255,.62)}
.touch-stick-base::after{content:"DI CHUYỂN";position:absolute;left:50%;top:calc(100% + 6px);transform:translateX(-50%);color:#fff;font-size:11px;font-weight:900;text-shadow:0 1px 3px #000;white-space:nowrap}
.touch-stick-knob{width:70px;height:70px;margin:-35px 0 0 -35px;background:rgba(255,255,255,.76);border:3px solid rgba(255,255,255,.95)}
@media(pointer:coarse){
  #fps{display:none}
  #crosshair{width:24px;height:24px}
  #hotbar{bottom:max(10px,env(safe-area-inset-bottom));gap:3px;padding:5px;border-radius:12px;background:rgba(0,0,0,.52)}
  .hotbar-slot{width:44px;height:44px}
  .hotbar-key{display:none}
  .touch-buttons{right:max(9px,env(safe-area-inset-right));bottom:calc(max(10px,env(safe-area-inset-bottom)) + 66px)}
}
@media(pointer:coarse) and (max-width:430px){
  .touch-button{width:72px;height:60px;font-size:13px}
  .touch-buttons{gap:6px}
  .hotbar-slot{width:39px;height:39px}
}
"""
write("src/style.css", s)

print("Đã Việt hóa toàn bộ phần giao diện người chơi.")
