"""disasm.py —— 把主脚本反汇编成可读清单（函数级，带常量与名字解析）。

用法:
    python disasm.py <garrison_farm.marshalled> [输出文件]

说明: Python 3.11 的字节码目前没有可用的自动反编译器（uncompyle6 只支持到 3.8；
pycdc 需要 C++ 工具链，且对 3.11 支持有限），所以这里输出的是**反汇编清单**：
每条指令、操作数、跳转目标、常量与变量名都解析出来，配合 replacements/ 里
已重写的函数源码，可以还原程序行为。

注意: 反汇编结果属于原程序的衍生内容，本仓库不收录生成的清单文件，
请自行在本地生成、自用。
"""

import dis
import io
import marshal
import sys
import types


def const_repr(value):
    if isinstance(value, types.CodeType):
        return '<code %s @%d>' % (value.co_name, value.co_firstlineno)
    text = repr(value)
    return text if len(text) <= 120 else text[:117] + '...'


def dump_function(code, out):
    args = code.co_varnames[:code.co_argcount]
    out.write('\n' + '=' * 78 + '\n')
    out.write('函数 %s  行 %d  参数(%s)\n' % (code.co_name, code.co_firstlineno, ', '.join(args)))
    out.write('  局部变量: %s\n' % ', '.join(code.co_varnames))
    if code.co_freevars:
        out.write('  闭包变量: %s\n' % ', '.join(code.co_freevars))
    out.write('-' * 78 + '\n')
    prev_line = None
    for ins in dis.get_instructions(code):
        if ins.starts_line and ins.starts_line != prev_line:
            out.write('\n  L%-4d ' % ins.starts_line)
            prev_line = ins.starts_line
        elif prev_line is None:
            out.write('\n        ')
            prev_line = -1
        arg = '' if ins.arg is None else str(ins.arg)
        extra = ''
        if ins.opname == 'LOAD_CONST':
            extra = '  ; ' + const_repr(ins.argval)
        elif ins.opname in ('LOAD_NAME', 'LOAD_GLOBAL', 'LOAD_ATTR', 'STORE_NAME',
                            'STORE_GLOBAL', 'STORE_ATTR', 'LOAD_FAST', 'STORE_FAST',
                            'DELETE_FAST', 'LOAD_DEREF', 'STORE_DEREF'):
            extra = '  ; ' + str(ins.argval)
        elif ins.opname.startswith(('JUMP', 'POP_JUMP', 'FOR_ITER')):
            extra = '  -> ' + str(ins.argval)
        out.write('    %-6d %-24s %-6s%s\n' % (ins.offset, ins.opname, arg, extra))


def walk(code):
    yield code
    for c in code.co_consts:
        if isinstance(c, types.CodeType):
            yield from walk(c)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        raise SystemExit(2)
    src = sys.argv[1]
    out_path = sys.argv[2] if len(sys.argv) > 2 else 'bytecode.txt'

    mod = marshal.loads(open(src, 'rb').read())
    buf = io.StringIO()
    buf.write('模块常量: %s\n' % ', '.join(const_repr(c) for c in mod.co_consts
                                           if not isinstance(c, types.CodeType)))
    funcs = [c for c in walk(mod) if c is not mod]
    buf.write('函数数量: %d\n' % len(funcs))
    for code in funcs:
        dump_function(code, buf)
    open(out_path, 'w', encoding='utf8').write(buf.getvalue())
    print('已写出 %s（%d 个函数，%d 字节）' % (out_path, len(funcs), len(buf.getvalue())))


if __name__ == '__main__':
    main()
