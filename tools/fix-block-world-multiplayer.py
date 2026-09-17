from pathlib import Path
import sys

root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('.')

main = root / 'src/main.ts'
s = main.read_text(encoding='utf-8')
s = s.replace('function showFatalError(error: unknown): void {', 'function showFatalError(_error: unknown): void {')
main.write_text(s, encoding='utf-8')

mp = root / 'src/multiplayer.ts'
s = mp.read_text(encoding='utf-8')
s = s.replace('private createAvatar(userId: string, name: string): RemoteAvatar | null {', 'private createAvatar(userId: string, name: string): RemoteAvatar | undefined {')
s = s.replace('if (!scene) return null;', 'if (!scene) return undefined;')
mp.write_text(s, encoding='utf-8')

print('Đã sửa lỗi TypeScript cho Block World multiplayer.')
