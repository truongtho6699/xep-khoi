from pathlib import Path
import sys

root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('.')

def p(name): return root / name
def read(name): return p(name).read_text(encoding='utf-8')
def write(name, s): p(name).write_text(s, encoding='utf-8')

# 1) HUD: trên điện thoại chỉ hiện tọa độ ngắn gọn, desktop giữ đầy đủ thông tin.
s = read('src/ui/hud.ts')
old = '    this.el.textContent = fps.toString() + " hình/giây · vị trí (" + pos + ") · " + info.chunks.toString() + " vùng · mã thế giới " + info.seed.toString() + note;\n'
new = '''    const mobileHud = window.matchMedia("(pointer: coarse)").matches || window.innerWidth <= 768;\n    if (mobileHud) {\n      const parts = pos.split(", ");\n      this.el.textContent = "📍 X " + parts[0] + " · Y " + parts[1] + " · Z " + parts[2];\n    } else {\n      this.el.textContent = fps.toString() + " hình/giây · vị trí (" + pos + ") · " + info.chunks.toString() + " vùng · mã thế giới " + info.seed.toString() + note;\n    }\n'''
if old in s:
    s = s.replace(old, new)
elif 'const mobileHud =' not in s:
    raise SystemExit('Không tìm thấy dòng HUD đã Việt hóa')
write('src/ui/hud.ts', s)

# 2) Bố trí lại giao diện mobile: tọa độ phía trên trái, CỨU phía trên phải.
s = read('src/style.css')
marker = '/* ===== Bố trí mobile Game Cá Voi ===== */'
if marker not in s:
    s += r'''

/* ===== Bố trí mobile Game Cá Voi ===== */
@media (pointer: coarse), (max-width:768px){
  #fps{
    display:block!important;
    top:max(58px,calc(env(safe-area-inset-top) + 52px))!important;
    left:max(10px,env(safe-area-inset-left))!important;
    right:auto!important;
    max-width:calc(100vw - 150px);
    padding:7px 10px;
    border-radius:999px;
    background:rgba(5,28,45,.72);
    border:1px solid rgba(255,255,255,.28);
    color:#fff!important;
    font:800 12px/1.15 Arial,sans-serif!important;
    text-shadow:0 1px 2px #000;
    white-space:nowrap;
    pointer-events:none;
    z-index:24!important;
  }

  #blockworld-rescue-button{
    top:max(102px,calc(env(safe-area-inset-top) + 96px))!important;
    right:max(10px,env(safe-area-inset-right))!important;
    bottom:auto!important;
    min-width:78px;
    min-height:42px;
    padding:9px 12px;
    font-size:13px;
    z-index:26;
  }

  /* Giữ riêng khu vực các nút chơi ở đáy màn hình. */
  .touch-buttons{
    right:max(8px,env(safe-area-inset-right))!important;
    bottom:calc(max(10px,env(safe-area-inset-bottom)) + 66px)!important;
  }
}

@media (pointer: coarse) and (max-width:430px){
  #fps{font-size:11px!important;padding:6px 8px;max-width:calc(100vw - 110px)}
  #blockworld-rescue-button{top:max(96px,calc(env(safe-area-inset-top) + 90px))!important;min-width:72px;padding:8px 10px}
}
'''
write('src/style.css', s)

print('Đã hiển thị tọa độ và bố trí lại nút CỨU riêng khỏi nút NHẢY trên mobile.')
