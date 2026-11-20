# 函数表

按原程序的反汇编整理（只列顶层函数，行号为原文件行号）。

## 设备与连接

| 行 | 函数 | 参数 | 字节码 |
|---|---|---|---|
| 36 | is_maa_dir | 1 | 154 |
| 40 | find_maa | 0 | 720 |
| 67 | running_paths | 1 | 236 |
| 78 | read_maa_connect | 1 | 1490 |
| 116 | <listcomp> | 1 | 36 |
| 123 | find_adb | 1 | 802 |
| 141 | adb_online | 1 | 196 |
| 150 | try_connect | 3 | 446 |
| 174 | check | 3 | 130 |
| 179 | fatal_box | 1 | 224 |
| 190 | is_admin | 0 | 132 |
| 198 | relaunch_as_admin | 0 | 524 |
| 216 | restore_window | 0 | 188 |
| 226 | setup_pc | 1 | 3504 |

## 截图 / OCR / 识别

| 行 | 函数 | 参数 | 字节码 |
|---|---|---|---|
| 705 | adb | 0 | 142 |
| 710 | shot | 0 | 746 |
| 733 | tap | 3 | 348 |
| 742 | swipe | 6 | 838 |
| 758 | touch | 3 | 306 |
| 767 | ocr | 2 | 472 |
| 782 | find | 1 | 94 |
| 788 | numrec | 2 | 332 |
| 801 | num | 2 | 220 |
| 809 | log | 0 | 410 |
| 818 | save | 2 | 170 |
| 823 | load_done | 0 | 226 |
| 830 | save_done | 1 | 176 |
| 834 | yellow_ratio | 2 | 192 |
| 844 | has_color_badge | 3 | 352 |
| 852 | has_badge | 3 | 174 |
| 856 | passed_count | 1 | 186 |
| 868 | grid_shift | 2 | 246 |
| 879 | detect_rows | 1 | 490 |
| 896 | scroll_grid | 0 | 220 |

## 选策略与摆位

| 行 | 函数 | 参数 | 字节码 |
|---|---|---|---|
| 906 | strategy_name | 1 | 452 |
| 913 | pick_strategy | 1 | 2068 |
| 1001 | set_profile | 1 | 84 |
| 1007 | match_key | 2 | 186 |
| 1015 | prio_index | 1 | 104 |
| 1022 | is_safe_op | 1 | 68 |
| 1026 | rank | 2 | 106 |
| 1036 | pick_squad | 0 | 404 |
| 1066 | Board | 0 | 20 |
| 1079 | read_shop | 1 | 376 |
| 1103 | is_healer | 1 | 98 |
| 1106 | is_dps | 1 | 154 |
| 1117 | shop_cards | 1 | 1086 |
| 1145 | buy | 2 | 714 |
| 1167 | green_tiles | 1 | 634 |
| 1184 | right3 | 2 | 932 |
| 1215 | drag_path | 5 | 320 |
| 1226 | bench_ops | 1 | 6 |
| 1240 | load_layout | 0 | 392 |

## 部署与买卖

| 行 | 函数 | 参数 | 字节码 |
|---|---|---|---|
| 1252 | is_green | 3 | 290 |
| 1258 | drag_name | 1 | 190 |
| 1265 | near | 3 | 62 |
| 1268 | deploy_from_bench | 4 | 100 |
| 1274 | deploy_from_bench_old | 4 | 1690 |
| 1333 | tile_order | 1 | 386 |
| 1341 | tile_xy | 1 | 176 |
| 1346 | deploy_layout | 5 | 2806 |
| 1449 | sell_at | 2 | 486 |
| 1460 | in_facing_mode | 1 | 120 |
| 1465 | set_facing | 3 | 412 |
| 1482 | slots_left | 1 | 52 |
| 1487 | locate_new | 2 | 626 |
| 1498 | new_bench_slot | 2 | 626 |
| 1510 | sell_lowest | 1 | 524 |
| 1526 | buy_and_deploy | 4 | 430 |
| 1544 | <listcomp> | 1 | 22 |
| 1545 | <listcomp> | 1 | 22 |
| 1547 | deploy_bench | 1 | 300 |
| 1567 | handle_popups | 0 | 170 |
| 1575 | read_gold | 2 | 252 |
| 1591 | gold_now | 0 | 200 |

## 回合与主循环

| 行 | 函数 | 参数 | 字节码 |
|---|---|---|---|
| 1601 | shop_signature | 1 | 52 |
| 1604 | prep_phase | 2 | 3440 |
| 1744 | main | 0 | 8436 |
