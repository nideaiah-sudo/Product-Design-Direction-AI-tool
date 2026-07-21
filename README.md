# 标准件生成 AI 工具

> 离线可用的螺丝 STEP 生成器：PDF 规格书 → 内六角杯头螺丝 STEP。

## 功能

- 从 PDF 规格书自动提取参数（如 M5x12 螺丝）
- 从螺丝照片 OCR 自动识别参数（如 M1.4*5）
- 根据 ISO / DIN / GB 标准尺寸补全缺失参数
- 支持多种头型：内六角杯头、十字盘头、十字圆头、十字沉头
- 支持多种尾部：平尾、尖尾
- 用 CadQuery 生成带真实三角螺纹的 STEP 文件
- 支持命令行批量生成
- 支持 tkinter 图形界面操作
- 可打包为独立 exe，离线运行

## 目录结构

```
D:\000a\standard-parts-ai
├── src\standard_parts_ai\     # Python 包
│   ├── __main__.py              # 入口：CLI/GUI 路由
│   ├── cli.py                   # 命令行入口
│   ├── app.py                   # tkinter GUI
│   ├── models.py                # 数据模型
│   ├── pdf_parser.py            # PDF 规格书解析
│   ├── standards.py             # ISO 标准表
│   └── generators.py            # CadQuery STEP 生成
├── tests\                       # 单元测试
├── requirements.txt             # Python 依赖
├── build_exe.py                 # PyInstaller 打包脚本
└── README.md                    # 本文件
```

## 安装

```bash
cd D:\000a\standard-parts-ai
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## 使用方式

### 1. 图形界面（默认）

```bash
python -m standard_parts_ai
```

双击运行打包后的 `dist\standard-parts-ai\standard-parts-ai.exe` 也可打开 GUI。

### 2. 命令行

```bash
# 单个 PDF 生成
python -m standard_parts_ai "Z:\项目文件\seeed标准库\自做\规格书\326010708_Screw;内六角杯头螺丝-304不锈钢-M5x12mm_表面钝化.pdf" --out-dir "Z:\项目文件\seeed标准库\自做\STEP"

# 图片识别生成（支持 jpg/png/bmp 等）
python -m standard_parts_ai "Z:\项目文件\seeed标准库\自做\图片\M1.4x5.jpg" --out-dir "Z:\项目文件\seeed标准库\自做\STEP"

# 批量生成
python -m standard_parts_ai "Z:\项目文件\seeed标准库\自做\规格书\*.pdf" --out-dir "Z:\项目文件\seeed标准库\自做\STEP"

# 手动模式（无需 PDF）
python -m standard_parts_ai --thread M5 --pitch 0.8 --length 12 --out-dir "Z:\项目文件\seeed标准库\自做\STEP"

# 指定头型、驱动、尾部
python -m standard_parts_ai --thread M5 --length 12 --head-type pan --drive-type cross --tail-type sharp --out-dir "Z:\项目文件\seeed标准库\自做\STEP"
```

支持的 `--head-type`：`socket`（内六角杯头）、`pan`（盘头）、`round`（圆头）、`countersunk`（沉头）
支持的 `--drive-type`：`hex`（内六角）、`cross`（十字）
支持的 `--tail-type`：`flat`（平尾）、`sharp`（尖尾）

## 打包为 exe

```bash
python build_exe.py
```

打包完成后，产物位于 `dist\standard-parts-ai\standard-parts-ai.exe`，连同同目录下的 `_internal` 文件夹一起拷贝到目标机器，双击即可离线运行。

> 注意：本工具使用 onedir 模式打包，`standard-parts-ai.exe` 与 `_internal` 文件夹必须放在同一目录下。

## 依赖

- Python 3.9+
- CadQuery >= 2.4.0
- PyPDF2 >= 3.0.0
- PyInstaller >= 6.0（仅打包需要）

## 联系我们

如果你在使用过程中遇到问题，或有任何功能建议，欢迎通过以下方式联系：

- **提交 Issue**：在 [Issues](../../issues) 页面提交 Bug 报告、功能建议或提问。
- **发送邮件**：[wxndxc@qq.com](mailto:wxndxc@qq.com)

我们会尽快回复。
