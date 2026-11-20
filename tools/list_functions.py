"""list_functions.py —— 列出主脚本里的所有函数（含行号、参数、常量摘要）。

用法:
    python list_functions.py <garrison_farm.marshalled> [函数名关键字]

配合 extract_main.py 使用：
    python extract_main.py 测试1.0.exe extracted
    python list_functions.py extracted/garrison_farm.marshalled pick
"""

import marshal
import sys
import types


def walk(code, depth=0):
    yield code, depth
    for c in code.co_consts:
        if isinstance(c, types.CodeType):
            yield from walk(c, depth + 1)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        raise SystemExit(2)
    mod = marshal.loads(open(sys.argv[1], 'rb').read())
    keyword = sys.argv[2] if len(sys.argv) > 2 else ''

    for code, depth in walk(mod):
        if keyword and keyword not in code.co_name:
            continue
        consts = [c for c in code.co_consts if not isinstance(c, types.CodeType)]
        shown = ', '.join(repr(c)[:40] for c in consts[:6])
        print('%s%-22s line=%-5d args=%-32s consts=[%s]' % (
            '  ' * depth, code.co_name, code.co_firstlineno,
            ','.join(code.co_varnames[:code.co_argcount]), shown))


if __name__ == '__main__':
    main()
