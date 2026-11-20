"""extract_main.py —— 从 PyInstaller onefile 里导出主脚本（garrison_farm）的 marshal 数据。

用法:
    python extract_main.py <程序.exe> [输出目录]

导出内容:
    <输出目录>/garrison_farm.marshalled   主脚本的 marshal 字节
    <输出目录>/toc.txt                    CArchive 条目列表
"""

import marshal
import os
import struct
import sys
import zlib

MAGIC = b'MEI\014\013\012\013\016'


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        raise SystemExit(2)
    exe = sys.argv[1]
    outdir = sys.argv[2] if len(sys.argv) > 2 else 'extracted'
    os.makedirs(outdir, exist_ok=True)

    raw = open(exe, 'rb').read()
    magic, pkg_len, toc_off, toc_len, pyver, pylib = struct.unpack('!8sIIII64s', raw[-88:])
    if magic != MAGIC:
        raise SystemExit('不是 PyInstaller onefile（cookie magic 不匹配）')
    arch_start = len(raw) - pkg_len
    toc = raw[arch_start + toc_off: arch_start + toc_off + toc_len]

    entries, pos = [], 0
    while pos < len(toc):
        (elen,) = struct.unpack('!i', toc[pos:pos + 4])
        e = toc[pos:pos + elen]
        doff, clen, ulen = struct.unpack('!III', e[4:16])
        flag, typ = e[16], chr(e[17])
        name_end = e.find(b'\0', 18)
        entries.append((typ, e[18:name_end].decode('utf8', 'replace'), doff, clen, ulen, flag))
        pos += elen

    lines = ['%s %s off=%d len=%d ulen=%d flag=%d' % e for e in entries]
    open(os.path.join(outdir, 'toc.txt'), 'w', encoding='utf8').write('\n'.join(lines))

    for typ, name, doff, clen, ulen, flag in entries:
        if name == 'garrison_farm':
            buf = raw[arch_start + doff: arch_start + doff + clen]
            if flag:
                buf = zlib.decompress(buf)
            path = os.path.join(outdir, 'garrison_farm.marshalled')
            open(path, 'wb').write(buf)
            print('已导出 %s (%d bytes, %d 个条目)' % (path, len(buf), len(entries)))
            break
    else:
        raise SystemExit('没找到 garrison_farm')


if __name__ == '__main__':
    main()
