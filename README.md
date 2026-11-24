# micro_contral · NV 色心实验用微波源与参考时钟子系统

本仓库归档 NV 色心实验用微波源的硬件设计成果、参考时钟子系统（`clktree`）原理图与网表核验报告、需求规格文档以及完整的 AI 辅助设计与优化对话记录。

---

## 目录结构

```text
micro_contral/
├── README.md                                       # 本文件（项目总览与原理图预览）
├── docs/
│   ├── clktree_audit_report.md                     # clktree 原理图重建与网表逐条对账报告
│   ├── conversation_log.md                         # 完整硬件设计与优化对话记录（Markdown）
│   ├── schematic_conventions.md                    # 沉淀的嘉立创 EDA 模块化布线与防重叠规范
│   └── requirements/
│       ├── _原始需求_微波源设计要求1009.docx         # 微波源原始需求文档
│       └── 参考时钟_选型与连接规格_v1.md              # 参考时钟子系统选型与连接规格书 v1
├── hardware/
│   ├── schematics/
│   │   ├── REF_CLOCK_v2.png                        # REF_CLOCK 页高清原理图（实线直连重排 v2）
│   │   └── CLK_DIST_v2.png                         # CLK_DIST 页高清原理图（实线直连重排 v2）
│   ├── netlist/
│   │   └── clktree_netlist.txt                     # 导出的 Protel 2.0 完整网表（66 网 / 101 器件）
│   └── easyeda/
│       └── README.md                               # 嘉立创 EDA .epro 工程源文件归档说明
└── scripts/
    └── netlist_verifier.py                         # Protel 2.0 网表自动化核验脚本
```

---

## `clktree` 参考时钟子系统核心成果

- **规模与校验**：共 **101 个位号**、**66 条命名网络**（0 条 `$...` 自动匿名网络）、**303 / 320 引脚连通**（其余 17 脚均为官方手册确认的 NC/未用脚），规格 §6 全部 **49 / 49** 信号与电源网络精确匹配。
- **详细核验与待确认项**：见 [docs/clktree_audit_report.md](./docs/clktree_audit_report.md)。

### 1. `REF_CLOCK` 页（外参考整形 + ADF4002 锁相环 + DAC8551 校准 + U18 OCXO + 低噪 LDO）

![REF_CLOCK_v2](./hardware/schematics/REF_CLOCK_v2.png)

### 2. `CLK_DIST` 页（LTC6957-2 正弦整形 + LMK1D1208 1:8 LVDS 扇出 + ÷10 参考输出）

![CLK_DIST_v2](./hardware/schematics/CLK_DIST_v2.png)

---

## 关联文档

- 📋 [原理图与网表完整对账报告](./docs/clktree_audit_report.md)
- 💬 [完整硬件设计对话记录](./docs/conversation_log.md)
- 📐 [嘉立创 EDA 原理图模块化布线与防重叠规范](./docs/schematic_conventions.md)
- 📄 [参考时钟选型与连接规格 v1](./docs/requirements/参考时钟_选型与连接规格_v1.md)
