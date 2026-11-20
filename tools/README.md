# 补丁工具说明

本目录是把「测试1.0」打到原版程序上的工具链。原版程序是第三方用 PyInstaller
onefile 打包的 Python 3.11 程序，闭源、没有源码；下列脚本通过**直接替换字节码**
的方式修改它的行为。

## 原理

PyInstaller onefile 的可执行文件末尾是一个 `CArchive`：

```
[程序本体 ...][CArchive 载荷][TOC][88 字节 cookie]
```

- cookie 结构 `!8sIIII64s`：magic(`MEI\014\013\012\013\016`)、包长、TOC 偏移、TOC 长度、
  Python 版本、库名；
- TOC 每条：`[条目长度][数据偏移][压缩后长度][原始长度][压缩标志][类型码][名字\0]`；
- 主脚本 `garrison_farm` 存的是 **marshal 序列化后 zlib 压缩**的模块代码对象。

所以流程是：解出主脚本 → `marshal.loads` → 替换 `co_consts` 里的目标函数代码对象
→ `marshal.dumps` + zlib → 重建 CArchive 和 cookie。其余条目原样复制。

## 用法

```bash
# 1. 导出主脚本（可选，用来看函数/常量）
python tools/extract_main.py 测试1.0.exe extracted
python tools/list_functions.py extracted/garrison_farm.marshalled pick_strategy

# 2. 打补丁（输出新 exe）
python tools/patch_tool.py 原版.exe 打补丁后.exe

# 3. 自检（连上模拟器后跑，会打印连接/截图/OCR 结果）
打补丁后.exe --check --yes
```

## patch_tool.py 做了什么

| 替换项 | 作用 |
|---|---|
| `pick_strategy` | 选策略：按列表顺序逐格点开检查、满 6 次/红标跳过、写缓存、自动翻页 |
| `scroll_grid` | 翻页拖动距离（900→220，约 780px） |
| `has_color_badge` | 彩标识别，上下多试几个偏移，避免网格差几十像素就认不出 |
| `LEAVE_TIMEOUT` | 30/90 → **180 秒**（选策略扫描要 30~45 秒，原值会误判"离开界面"而中止） |

替换后的函数源码在 `replacements/`：

- `new_pick.py` —— 逐格检查 + `checked_full.json` 缓存 + 翻页
- `new_scroll.py` —— 滑动距离
- `new_badge.py` —— 彩标取色判定

## 校验

`patch_tool.py` 内置三道检查：

1. TOC 长度必须不变（否则说明不是同版本打包，直接拒绝写出）；
2. 三个函数都必须被替换成功；
3. 替换后按变量名/常量特征复查（`mem`、`220`、`0.12`）。

用同一份原版 exe 重新跑一次，输出应与已发布的 `测试1.0.exe` **字节完全一致**
（SHA256 相同，已实测）。

## 已知限制

- 只能处理**同一 Python 3.11** 打包的 onefile；换 Python 版本后 marshal 格式不兼容；
- 原版更新后函数行号/变量名可能变化，替换前先用 `list_functions.py` 确认；
- 这是对第三方程序的修改，仅用于学习交流，请勿用于商业用途。
