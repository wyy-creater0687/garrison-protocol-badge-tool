"""patch_tool.py —— 给 PyInstaller onefile 打包的「卫戍协议刷标工具」打补丁。

用法:
    python patch_tool.py <原版.exe> <输出.exe>

做的事:
  1. 定位 CArchive 里名为 garrison_farm 的主脚本（zlib 压缩的 marshal 代码对象）；
  2. 用 replacements/ 下的新版函数替换 pick_strategy / scroll_grid / has_color_badge；
  3. 把模块常量 LEAVE_TIMEOUT 从 30 秒放宽到 180 秒（选策略扫描要 30~45 秒，
     原值会被误判成"离开卫戍协议界面"而中止）；
  4. 重新 marshal + zlib，重建 CArchive、TOC 和 88 字节 cookie，其余数据原样保留。

依赖: 仅标准库（struct / zlib / marshal / types）。
注意: 目标必须是同一 Python 3.11 版本打包的 onefile；patch 后请先跑 --check 自检。
"""

import marshal
import os
import struct
import sys
import types
import zlib

MAGIC = b'MEI\014\013\012\013\016'
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from replacements.new_pick import SRC as PICK_SRC      # noqa: E402
from replacements.new_scroll import SRC as SCROLL_SRC  # noqa: E402
from replacements.new_badge import SRC as BADGE_SRC    # noqa: E402

# 替换后用于校验的标记
CHECKS = {
    'pick_strategy': lambda c: 'mem' in c.co_varnames,
    'scroll_grid': lambda c: 220 in [x for x in c.co_consts if isinstance(x, int)],
    'has_color_badge': lambda c: 0.12 in [x for x in c.co_consts if isinstance(x, float)],
}


def build(source, name, lineno):
    ns = {}
    exec(compile(source, 'garrison_farm.py', 'exec'), ns)
    return ns[name].__code__.replace(co_filename='garrison_farm.py', co_firstlineno=lineno)


def read_archive(raw):
    cookie = struct.unpack('!8sIIII64s', raw[-88:])
    if cookie[0] != MAGIC:
        raise SystemExit('不是 PyInstaller onefile（cookie magic 不匹配）')
    pkg_len, toc_off, toc_len, pyver, pylib = cookie[1], cookie[2], cookie[3], cookie[4], cookie[5]
    arch_start = len(raw) - pkg_len
    toc = raw[arch_start + toc_off: arch_start + toc_off + toc_len]
    entries, pos = [], 0
    while pos < len(toc):
        (elen,) = struct.unpack('!i', toc[pos:pos + 4])
        e = toc[pos:pos + elen]
        doff, clen, ulen = struct.unpack('!III', e[4:16])
        flag, typ = e[16], chr(e[17])
        name_end = e.find(b'\0', 18)
        entries.append(dict(
            elen=elen, doff=doff, clen=clen, ulen=ulen, flag=flag, typ=typ,
            name=e[18:name_end].decode('utf8', 'replace'),
        ))
        pos += elen
    return dict(raw=raw, arch_start=arch_start, pkg_len=pkg_len, toc_len=toc_len,
                pyver=pyver, pylib=pylib, entries=entries, payload=raw[:arch_start])


def patch(exe_in, exe_out):
    arc = read_archive(open(exe_in, 'rb').read())
    entries = arc['entries']
    target = next((e for e in entries if e['name'] == 'garrison_farm'), None)
    if not target:
        raise SystemExit('CArchive 里找不到 garrison_farm')

    blob = arc['raw'][arc['arch_start'] + target['doff']:
                      arc['arch_start'] + target['doff'] + target['clen']]
    if target['flag']:
        blob = zlib.decompress(blob)
    mod = marshal.loads(blob)

    new_codes = {
        'pick_strategy': build(PICK_SRC, 'pick_strategy', 913),
        'scroll_grid': build(SCROLL_SRC, 'scroll_grid', 896),
        'has_color_badge': build(BADGE_SRC, 'has_color_badge', 844),
    }

    consts = list(mod.co_consts)
    replaced = set()
    for i, c in enumerate(consts):
        if isinstance(c, types.CodeType) and c.co_name in new_codes:
            consts[i] = new_codes[c.co_name]
            replaced.add(c.co_name)
        elif isinstance(c, int) and not isinstance(c, bool) and c in (30, 90):
            consts[i] = 180          # LEAVE_TIMEOUT
    missing = set(new_codes) - replaced
    if missing:
        raise SystemExit('这些函数没找到: ' + ', '.join(sorted(missing)))

    new_mod = mod.replace(co_consts=tuple(consts))
    names = {c.co_name: c for c in new_mod.co_consts if isinstance(c, types.CodeType)}
    for fn, check in CHECKS.items():
        if not check(names[fn]):
            raise SystemExit('替换校验失败: ' + fn)

    new_blob = zlib.compress(marshal.dumps(new_mod), 9)
    payload = bytearray()
    new_toc = bytearray()
    for e in entries:
        if e['name'] == 'garrison_farm':
            data, clen, ulen, flag = new_blob, len(new_blob), len(marshal.dumps(new_mod)), 1
        elif e['clen'] == 0:
            data, clen, ulen, flag = b'', 0, 0, 0
        else:
            data = arc['raw'][arc['arch_start'] + e['doff']:
                              arc['arch_start'] + e['doff'] + e['clen']]
            clen, ulen, flag = e['clen'], e['ulen'], e['flag']
        doff = len(payload)
        payload += data
        body = struct.pack('!IIIBB', doff, clen, ulen, flag, ord(e['typ'])) + e['name'].encode('utf8')
        body += b'\0' * (e['elen'] - 4 - len(body))
        new_toc += struct.pack('!i', e['elen']) + body

    if len(new_toc) != arc['toc_len']:
        raise SystemExit('TOC 长度变化，拒绝写出（可能不是同版本打包）')

    pkg = bytes(payload) + bytes(new_toc)
    cookie = struct.pack('!8sIIII64s', MAGIC, len(pkg) + 88, len(payload), len(new_toc),
                         arc['pyver'], arc['pylib'])
    open(exe_out, 'wb').write(arc['payload'] + pkg + cookie)
    print('wrote %s (%d bytes)' % (exe_out, os.path.getsize(exe_out)))


if __name__ == '__main__':
    if len(sys.argv) != 3:
        print(__doc__)
        raise SystemExit(2)
    patch(sys.argv[1], sys.argv[2])
