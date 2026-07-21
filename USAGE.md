# standard-parts-ai 使用说明书

> 离线标准件（螺丝）STEP 生成工具：PDF 规格书 / 图片 OCR → 3D STEP 模型。

---

## 1. 快速开始

### 1.1 运行环境

- Windows 10 / 11
- 64 位系统

### 1.2 运行方式

解压或打开打包后的目录：

```text
D:\000a\standard-parts-ai\dist\standard-parts-ai\standard-parts-ai.exe
```

双击 `standard-parts-ai.exe` 即可启动图形界面（GUI）。

> 注意：`standard-parts-ai.exe` 与同级 `_internal` 文件夹必须在同一目录下，不可分开。

---

## 2. 图形界面（GUI）

### 2.1 界面布局

启动后，主界面包含：

1. **输入文件**：选择 PDF 规格书或螺丝照片（jpg/png 等）。
2. **输出目录**：选择 STEP 文件保存位置，默认 `STEP` 文件夹。
3. **螺丝类型**：
   - 头型：内六角杯头（socket）、盘头（pan）、圆头（round）、沉头（countersunk）
   - 驱动：内六角（hex）、十字（cross）
   - 尾部：平尾（flat）、尖尾（sharp）
4. **解析结果**：显示识别到的规格、外径、底孔、头高等参数。
5. **日志/进度条**：显示生成状态和报错信息。
6. **按钮**：
   - 解析输入：仅解析文件中的参数。
   - 生成 STEP：解析 + 生成 3D 模型。

### 2.2 使用步骤

1. 点击 **浏览...**，选择 PDF 规格书或图片。
2. 点击 **选择...**，选择输出目录。
3. 程序会自动识别参数并填充“头型 / 驱动 / 尾部”。
4. 如需手动修改类型，可直接在组合框中选择。
5. 点击 **生成 STEP**，等待进度条完成。
6. 生成的 STEP 文件位于选择的输出目录中。

---

## 3. 命令行（CLI）

在 `cmd` 或 PowerShell 中进入程序目录后运行：

```bash
cd D:\000a\standard-parts-ai
python -m standard_parts_ai <输入> --out-dir <输出目录>
```

> 开发/调试模式：`set PYTHONPATH=src` 后再执行。

### 3.1 常用命令

```bash
# 1. 单个 PDF 生成 STEP
python -m standard_parts_ai "Z:\规格书\M5x12.pdf" --out-dir "Z:\STEP"

# 2. 单个图片生成 STEP
python -m standard_parts_ai "Z:\图片\M3x8.jpg" --out-dir "Z:\STEP"

# 3. 批量生成（通配符）
python -m standard_parts_ai "Z:\规格书\*.pdf" --out-dir "Z:\STEP"

# 4. 手动指定参数（无需 PDF / 图片）
python -m standard_parts_ai --thread M5 --pitch 0.8 --length 12 --out-dir "Z:\STEP"

# 5. 手动指定头型、驱动、尾部
python -m standard_parts_ai --thread M5 --length 12 \
    --head-type pan --drive-type cross --tail-type sharp \
    --out-dir "Z:\STEP"
```

### 3.2 参数说明

| 参数 | 说明 | 示例 |
|---|---|---|
| `input` | PDF 规格书或图片路径，支持通配符 | `"规格书/*.pdf"` |
| `--out-dir` | 输出目录，默认 `STEP` | `--out-dir Z:\STEP` |
| `--thread` | 手动指定螺纹，如 M3、M5、M8 | `--thread M5` |
| `--pitch` | 螺距（手动模式） | `--pitch 0.8` |
| `--length` | 螺杆长度（手动模式） | `--length 12` |
| `--part-no` | 料号（手动模式） | `--part-no 326010708` |
| `--head-type` | 头型：`socket` / `pan` / `round` / `countersunk` | `--head-type pan` |
| `--drive-type` | 驱动：`hex` / `cross` | `--drive-type cross` |
| `--tail-type` | 尾部：`flat` / `sharp` | `--tail-type sharp` |

---

## 4. 支持的螺丝类型

| 头型 | head-type | 驱动说明 |
|---|---|---|
| 内六角杯头 | `socket` | 内六角 hex |
| 盘头 | `pan` | 十字 cross |
| 圆头 | `round` | 十字 cross |
| 沉头 | `countersunk` | 十字 cross |

| 驱动 | drive-type | 说明 |
|---|---|---|
| 内六角 | `hex` | 头部内六角孔 |
| 十字 | `cross` | 头部十字槽 |

| 尾部 | tail-type | 说明 |
|---|---|---|
| 平尾 | `flat` | 底端平整 |
| 尖尾 | `sharp` | 底端逐渐变尖 |

---

## 5. 输出结果

### 5.1 文件名

```text
{part_no}.step
```

例如：`326010708.step`、`M5x12.step`。

### 5.2 参数说明

生成成功后，日志和解析结果会显示：

```text
M5x12 螺丝
  Thread: M5.0 x 0.80 - 6g
  Length: 12.00 mm
  Major d: 5.000 mm (outer)      <- 螺纹大径
  Minor d: 4.134 mm (tap / 底孔) <- 攻丝/底孔直径
  Head: d=8.50 x h=5.00 mm (socket)
  Drive: hex
  Tail: flat
```

- **Major d**：螺纹外径，用于配合孔。
- **Minor d**：螺纹小径，加工时的底孔/攻丝参考。

---

## 6. 从 PDF 规格书解析

工具会自动从 PDF 文本中提取：

- 螺纹规格（如 `M5x0.8`）
- 螺杆长度
- 头部直径 / 头高
- 头型、驱动、尾部关键词

如果 PDF 是扫描件或图片型 PDF，需要先用 OCR；当前版本优先处理文字型 PDF。

---

## 7. 从图片 OCR 识别

工具内置 Tesseract OCR，可从螺丝照片中识别文字。

- 支持格式：`jpg`、`png`、`jpeg`、`bmp`、`tiff`、`webp`
- 识别的文字规格示例：`M1.4*5`、`M3x8` 等

> 注意：OCR 对拍摄角度、光线、模糊图片敏感，识别后建议在 GUI 中核对参数。

---

## 8. 常见问题

### Q1：双击 exe 无反应

- 检查 `standard-parts-ai.exe` 和 `_internal` 文件夹是否在同一目录。
- 尝试从命令行运行，查看报错信息。

### Q2：PDF 解析失败

- 确认 PDF 是文字型 PDF，不是纯图片。
- 检查文件名中是否包含螺纹规格，如 `M5x12`。

### Q3：生成的 STEP 在 CAD 中打不开

- 确认 CAD 软件支持 STEP AP203/214。
- 尝试用 FreeCAD、Fusion 360 等软件打开。

### Q4：OCR 识别不准确

- 确保图片清晰、文字水平。
- 放大图片后再识别。

### Q5：头部正确，但螺纹是简化圆柱

这是正常设计。当前版本为了兼顾生成速度和稳定性，螺杆采用大径圆柱简化表示；配合头部几何和参数显示，已能满足标准件库管理需求。

---

## 9. 目录结构

```text
D:\000a\standard-parts-ai
├── dist\standard-parts-ai\           # 打包后的可执行文件
│   ├── standard-parts-ai.exe
│   └── _internal\                    # 依赖库
├── src\standard_parts_ai\             # Python 源代码
│   ├── generators.py                  # 3D 几何生成
│   ├── pdf_parser.py                  # PDF 规格书解析
│   ├── image_parser.py                # 图片 OCR
│   ├── standards.py                   # 标准尺寸表
│   ├── models.py                      # 数据模型
│   ├── app.py                         # GUI
│   ├── cli.py                         # 命令行
│   └── ...
├── tests\                             # 单元测试
├── tesseract\                         # OCR 引擎
├── test_output\                       # 示例 STEP 输出
├── README.md
├── USAGE.md                           # 本说明书
└── build_exe.py                       # 打包脚本
```

---

## 10. 重新打包

修改代码后，如需重新生成 exe：

```bash
cd D:\000a\standard-parts-ai
python build_exe.py
```

打包完成后，新的 exe 位于 `dist\standard-parts-ai\standard-parts-ai.exe`。

---

## 11. 联系方式

内部工具，仅供 seeed 标准库项目使用。

如有问题，可查看日志输出或检查 `tests` 目录下的单元测试是否通过：

```bash
set PYTHONPATH=src
python -m unittest discover -s tests -v
```
