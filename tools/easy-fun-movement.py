from pathlib import Path
import sys

root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('.')

def p(name): return root / name
def read(name): return p(name).read_text(encoding='utf-8')
def write(name, s): p(name).write_text(s, encoding='utf-8')

# 1) PlayerController: tự nhảy bậc 1 khối + ghi nhớ điểm an toàn + cứu hộ.
s = read('src/player/controller.ts')

if 'private safePosition' not in s:
    s = s.replace(
        '  private lockWatchdog: ReturnType<typeof setTimeout> | undefined;\n',
        '  private lockWatchdog: ReturnType<typeof setTimeout> | undefined;\n'
        '  private safePosition: { x: number; y: number; z: number };\n'
        '  private safeCheckTimer = 0;\n'
        '  private lastRescueAt = 0;\n'
    )

    s = s.replace(
        '    this.state = {\n      position: { x: spawnX, y: groundY, z: spawnZ },\n      velocity: { x: 0, y: 0, z: 0 },\n      onGround: false,\n    };\n',
        '    this.state = {\n      position: { x: spawnX, y: groundY, z: spawnZ },\n      velocity: { x: 0, y: 0, z: 0 },\n      onGround: false,\n    };\n'
        '    this.safePosition = { x: spawnX, y: groundY, z: spawnZ };\n'
    )

    old = '''  update(dt: number): void {
    if (this.controlMode !== "idle") {
      const { forward, right, jump, sprint } = this.currentInput();
      this.state = stepPhysics(
        this.state,
        { forward, right, jump, sprint, yaw: this.yaw },
        dt,
        (x, y, z) => isSolid(this.world.getBlock(x, y, z)),
        (x, y, z) => this.world.getBlock(x, y, z) === BlockId.WATER,
      );
    }
    this.syncCamera();
  }
'''
    new = '''  private isSafeStandingSpot(): boolean {
    if (!this.state.onGround) return false;
    const x = Math.floor(this.state.position.x);
    const y = Math.floor(this.state.position.y);
    const z = Math.floor(this.state.position.z);
    const solid = (xx: number, yy: number, zz: number) => isSolid(this.world.getBlock(xx, yy, zz));
    const open = (xx: number, zz: number) =>
      solid(xx, y - 1, zz) && !solid(xx, y, zz) && !solid(xx, y + 1, zz);
    return open(x, z) && open(x + 1, z) && open(x - 1, z) && open(x, z + 1) && open(x, z - 1);
  }

  rescue(): void {
    const now = performance.now();
    if (now - this.lastRescueAt < 700) return;
    this.lastRescueAt = now;
    this.state = {
      position: { ...this.safePosition },
      velocity: { x: 0, y: 0, z: 0 },
      onGround: false,
    };
    this.syncCamera();
    window.dispatchEvent(new CustomEvent('blockworld-rescued'));
  }

  update(dt: number): void {
    if (this.controlMode !== "idle") {
      let { forward, right, jump, sprint } = this.currentInput();

      // Trợ giúp cho trẻ nhỏ: gặp bậc cao 1 khối sẽ tự nhảy nếu phía trên thoáng.
      if (!jump && this.state.onGround && (Math.abs(forward) > 0.18 || Math.abs(right) > 0.18)) {
        let dx = -Math.sin(this.yaw) * forward + Math.cos(this.yaw) * right;
        let dz = -Math.cos(this.yaw) * forward - Math.sin(this.yaw) * right;
        const len = Math.hypot(dx, dz) || 1;
        dx /= len;
        dz /= len;
        const tx = Math.floor(this.state.position.x + dx * 0.65);
        const tz = Math.floor(this.state.position.z + dz * 0.65);
        const fy = Math.floor(this.state.position.y + 0.05);
        const stepAhead = isSolid(this.world.getBlock(tx, fy, tz));
        const headClear = !isSolid(this.world.getBlock(tx, fy + 1, tz)) && !isSolid(this.world.getBlock(tx, fy + 2, tz));
        if (stepAhead && headClear) jump = true;
      }

      this.state = stepPhysics(
        this.state,
        { forward, right, jump, sprint, yaw: this.yaw },
        dt,
        (x, y, z) => isSolid(this.world.getBlock(x, y, z)),
        (x, y, z) => this.world.getBlock(x, y, z) === BlockId.WATER,
      );

      this.safeCheckTimer += dt;
      if (this.safeCheckTimer >= 0.45) {
        this.safeCheckTimer = 0;
        if (this.isSafeStandingSpot()) this.safePosition = { ...this.state.position };
      }

      // Rơi xuống hố sâu thì tự đưa về điểm an toàn gần nhất.
      if (this.state.position.y < this.safePosition.y - 9 || this.state.position.y < 2) {
        this.rescue();
      }
    }
    this.syncCamera();
  }
'''
    if old not in s:
        raise SystemExit('Không tìm thấy đoạn update PlayerController để vá')
    s = s.replace(old, new)
write('src/player/controller.ts', s)

# 2) Nút CỨU nổi, luôn dễ bấm trên điện thoại.
s = read('src/main.ts')
if 'blockworld-rescue-button' not in s:
    needle = '  const player = new PlayerController(view.camera, view.domElement, world, spawn.x, spawn.z);\n'
    insert = '''  const player = new PlayerController(view.camera, view.domElement, world, spawn.x, spawn.z);

  const rescueButton = document.createElement('button');
  rescueButton.id = 'blockworld-rescue-button';
  rescueButton.type = 'button';
  rescueButton.textContent = '🛟 CỨU';
  rescueButton.setAttribute('aria-label', 'Đưa con ra khỏi chỗ bị mắc kẹt');
  rescueButton.addEventListener('click', (event) => {
    event.preventDefault();
    event.stopPropagation();
    player.rescue();
  });
  document.body.appendChild(rescueButton);

  const rescueToast = document.createElement('div');
  rescueToast.id = 'blockworld-rescue-toast';
  rescueToast.textContent = '✨ Đã đưa con về chỗ an toàn';
  document.body.appendChild(rescueToast);
  window.addEventListener('blockworld-rescued', () => {
    rescueToast.classList.add('show');
    window.setTimeout(() => rescueToast.classList.remove('show'), 1300);
  });
'''
    if needle not in s:
        raise SystemExit('Không tìm thấy chỗ tạo PlayerController')
    s = s.replace(needle, insert)
write('src/main.ts', s)

# 3) Giao diện nút cứu.
s = read('src/style.css')
if '#blockworld-rescue-button' not in s:
    s += r'''

/* ===== Chế độ di chuyển dễ cho trẻ nhỏ ===== */
#blockworld-rescue-button{
  position:fixed;z-index:25;right:max(14px,env(safe-area-inset-right));
  bottom:max(92px,calc(env(safe-area-inset-bottom) + 82px));
  border:2px solid rgba(255,255,255,.75);border-radius:999px;
  padding:12px 16px;background:rgba(13,94,150,.88);color:#fff;
  font:900 14px Arial,sans-serif;box-shadow:0 5px 16px rgba(0,0,0,.32);
  -webkit-tap-highlight-color:transparent;touch-action:manipulation
}
#blockworld-rescue-button:active{transform:scale(.95)}
#blockworld-rescue-toast{
  position:fixed;z-index:40;left:50%;top:18%;transform:translate(-50%,-10px);
  opacity:0;pointer-events:none;padding:10px 14px;border-radius:999px;
  background:rgba(8,45,70,.9);color:#fff;font:800 13px Arial,sans-serif;
  transition:.2s;white-space:nowrap
}
#blockworld-rescue-toast.show{opacity:1;transform:translate(-50%,0)}
@media(pointer:fine){#blockworld-rescue-button{bottom:28px}}
'''
write('src/style.css', s)

print('Đã thêm tự nhảy bậc, tự cứu khi rơi sâu và nút CỨU.')
