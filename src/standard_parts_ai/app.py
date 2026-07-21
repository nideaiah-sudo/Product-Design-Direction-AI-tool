# -*- coding: utf-8 -*-
"""tkinter 图形界面入口."""

from __future__ import annotations

import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, ttk

from .generators import generate_step
from .image_parser import parse_image
from .models import ScrewParams
from .pdf_parser import parse_pdf
from .standards import (
    default_pitch,
    get_cross_drive_size,
    lookup_gb_standard,
    lookup_iso,
)


class StdPartsAIApp:
    """标准件生成 AI 工具主窗口."""

    # 显示中文 → 内部英文 的映射
    _HEAD_TYPE_DISP = {"内六角杯头": "socket", "盘头": "pan", "圆头": "round", "沉头": "countersunk"}
    _DRIVE_TYPE_DISP = {"内六角": "hex", "十字": "cross"}
    _TAIL_TYPE_DISP = {"平尾": "flat", "尖尾": "sharp"}

    # 可手动修正的参数（中文显示 → 字段名）
    _PARAM_FIELDS: tuple[tuple[str, str], ...] = (
        ("螺纹大径", "major_d"),
        ("螺　　距", "pitch"),
        ("螺杆长度", "length"),
        ("头部直径", "head_d"),
        ("头部高度", "head_h"),
        ("六角对边/槽号", "hex_size"),
    )

    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("标准件生成 AI 工具 - 螺丝 STEP 生成")
        self.root.geometry("560x760")
        self.root.resizable(False, False)

        self.input_path = tk.StringVar()
        self.out_dir = tk.StringVar(value=str(Path.cwd() / "STEP"))

        # 类型选择（存储中文显示值）
        self.head_type = tk.StringVar(value="内六角杯头")
        self.drive_type = tk.StringVar(value="内六角")
        self.tail_type = tk.StringVar(value="平尾")

        # 参数修正输入框
        self.param_vars: dict[str, tk.StringVar] = {
            "major_d": tk.StringVar(),
            "pitch": tk.StringVar(),
            "length": tk.StringVar(),
            "head_d": tk.StringVar(),
            "head_h": tk.StringVar(),
            "hex_size": tk.StringVar(),
        }

        # 最近一次解析得到的原始参数
        self._last_params: ScrewParams | None = None

        self._build_ui()

    def _build_ui(self) -> None:
        # 标题
        tk.Label(self.root, text="标准件生成 AI 工具", font=("Microsoft YaHei", 16, "bold")).pack(pady=10)
        tk.Label(self.root, text="PDF / 图片 → 螺丝 STEP", fg="gray").pack()

        # 输入选择
        input_frame = tk.Frame(self.root)
        input_frame.pack(fill="x", padx=20, pady=10)
        tk.Label(input_frame, text="输入文件:").pack(side="left")
        tk.Entry(input_frame, textvariable=self.input_path, width=35).pack(side="left", padx=5)
        tk.Button(input_frame, text="浏览...", command=self._browse_input).pack(side="left")

        # 输出目录
        out_frame = tk.Frame(self.root)
        out_frame.pack(fill="x", padx=20, pady=5)
        tk.Label(out_frame, text="输出目录:").pack(side="left")
        tk.Entry(out_frame, textvariable=self.out_dir, width=35).pack(side="left", padx=5)
        tk.Button(out_frame, text="选择...", command=self._browse_out_dir).pack(side="left")

        # 类型选择
        type_frame = tk.LabelFrame(self.root, text="螺丝类型", padx=10, pady=5)
        type_frame.pack(fill="x", padx=20, pady=10)

        tk.Label(type_frame, text="头型:").grid(row=0, column=0, sticky="w")
        head_combo = ttk.Combobox(
            type_frame,
            textvariable=self.head_type,
            values=list(self._HEAD_TYPE_DISP.keys()),
            state="readonly",
            width=12,
        )
        head_combo.grid(row=0, column=1, padx=5)

        tk.Label(type_frame, text="驱动:").grid(row=0, column=2, sticky="w", padx=(20, 0))
        drive_combo = ttk.Combobox(
            type_frame,
            textvariable=self.drive_type,
            values=list(self._DRIVE_TYPE_DISP.keys()),
            state="readonly",
            width=12,
        )
        drive_combo.grid(row=0, column=3, padx=5)

        tk.Label(type_frame, text="尾部:").grid(row=1, column=0, sticky="w", pady=(10, 0))
        tail_combo = ttk.Combobox(
            type_frame,
            textvariable=self.tail_type,
            values=list(self._TAIL_TYPE_DISP.keys()),
            state="readonly",
            width=12,
        )
        tail_combo.grid(row=1, column=1, padx=5, pady=(10, 0))

        # 参数修正
        param_frame = tk.LabelFrame(self.root, text="参数修正（点击“调整”后编辑）", padx=10, pady=5)
        param_frame.pack(fill="x", padx=20, pady=10)

        self._param_entries: dict[str, tk.Entry] = {}
        for idx, (label, field) in enumerate(self._PARAM_FIELDS):
            row, col = divmod(idx, 2)
            tk.Label(param_frame, text=f"{label}:").grid(row=row, column=col * 2, sticky="w", pady=2)
            entry = tk.Entry(param_frame, textvariable=self.param_vars[field], width=12, state="readonly")
            entry.grid(row=row, column=col * 2 + 1, padx=5, pady=2, sticky="w")
            self._param_entries[field] = entry

        # 功能按钮
        tk.Button(param_frame, text="调整", command=self._enable_param_edit, width=10).grid(
            row=len(self._PARAM_FIELDS) // 2 + 1, column=0, pady=5
        )
        tk.Button(param_frame, text="按标准重置", command=self._reset_params_to_standard, width=12).grid(
            row=len(self._PARAM_FIELDS) // 2 + 1, column=1, columnspan=3, pady=5
        )

        # 解析结果
        tk.Label(self.root, text="解析结果：", anchor="w").pack(fill="x", padx=20, pady=(10, 0))
        self.result_box = tk.Text(self.root, height=10, state="disabled", bg="#f8f8f8")
        self.result_box.pack(fill="both", padx=20, pady=5)

        # 操作按钮
        btn_frame = tk.Frame(self.root)
        btn_frame.pack(fill="x", padx=20, pady=10)
        tk.Button(btn_frame, text="生成 STEP", command=self._generate_step, width=12, bg="#4CAF50", fg="white").pack(side="left", padx=5)
        tk.Button(btn_frame, text="退出", command=self.root.quit, width=12).pack(side="right", padx=5)

        # 日志
        tk.Label(self.root, text="日志：", anchor="w").pack(fill="x", padx=20, pady=(10, 0))
        self.log_box = scrolledtext.ScrolledText(self.root, height=8, state="disabled", bg="#1e1e1e", fg="#00ff00")
        self.log_box.pack(fill="both", padx=20, pady=5)

        # 进度条
        self.progress = ttk.Progressbar(self.root, mode="indeterminate")
        self.progress.pack(fill="x", padx=20, pady=5)

    def _log(self, message: str) -> None:
        self.log_box.config(state="normal")
        self.log_box.insert("end", message + "\n")
        self.log_box.see("end")
        self.log_box.config(state="disabled")

    def _set_result(self, text: str) -> None:
        self.result_box.config(state="normal")
        self.result_box.delete("1.0", "end")
        self.result_box.insert("1.0", text)
        self.result_box.config(state="disabled")

    def _browse_input(self) -> None:
        path = filedialog.askopenfilename(
            title="选择 PDF 规格书或图片",
            filetypes=[
                ("PDF 文件", "*.pdf"),
                ("图片文件", "*.png;*.jpg;*.jpeg;*.bmp;*.tiff;*.webp"),
                ("所有文件", "*.*"),
            ],
        )
        if path:
            self.input_path.set(path)
            self._auto_parse()

    def _browse_out_dir(self) -> None:
        path = filedialog.askdirectory(title="选择输出目录")
        if path:
            self.out_dir.set(path)

    def _get_head_type(self) -> str:
        """获取英文头型."""
        return self._HEAD_TYPE_DISP.get(self.head_type.get(), self.head_type.get())

    def _set_head_type(self, value: str) -> None:
        """设置中文头型."""
        for cn, en in self._HEAD_TYPE_DISP.items():
            if en == value:
                self.head_type.set(cn)
                return
        self.head_type.set(value)

    def _get_drive_type(self) -> str:
        """获取英文驱动类型."""
        return self._DRIVE_TYPE_DISP.get(self.drive_type.get(), self.drive_type.get())

    def _set_drive_type(self, value: str) -> None:
        """设置中文驱动类型."""
        for cn, en in self._DRIVE_TYPE_DISP.items():
            if en == value:
                self.drive_type.set(cn)
                return
        self.drive_type.set(value)

    def _get_tail_type(self) -> str:
        """获取英文尾部类型."""
        return self._TAIL_TYPE_DISP.get(self.tail_type.get(), self.tail_type.get())

    def _set_tail_type(self, value: str) -> None:
        """设置中文尾部类型."""
        for cn, en in self._TAIL_TYPE_DISP.items():
            if en == value:
                self.tail_type.set(cn)
                return
        self.tail_type.set(value)

    def _set_params_from_model(self, params: ScrewParams) -> None:
        """把解析结果填入参数修正框."""
        self.param_vars["major_d"].set(str(params.major_d))
        self.param_vars["pitch"].set(str(params.pitch))
        self.param_vars["length"].set(str(params.length))
        self.param_vars["head_d"].set(str(params.head_d))
        self.param_vars["head_h"].set(str(params.head_h))
        hex_val = params.hex_size if params.drive_type == "hex" else params.cross_drive_size
        self.param_vars["hex_size"].set(str(hex_val))

    def _build_params_from_model(self, params: ScrewParams) -> ScrewParams:
        """合并用户手动修正与解析结果，返回新的 ScrewParams."""
        def _float_field(name: str, default: float) -> float:
            try:
                return float(self.param_vars[name].get().strip())
            except (ValueError, TypeError):
                return default

        major_d = _float_field("major_d", params.major_d)
        pitch = _float_field("pitch", params.pitch)
        length = _float_field("length", params.length)
        head_d = _float_field("head_d", params.head_d)
        head_h = _float_field("head_h", params.head_h)
        hex_size = _float_field("hex_size", params.hex_size)
        cross_drive_size = str(int(hex_size)) if params.drive_type == "cross" else params.cross_drive_size

        iso = lookup_iso(major_d, self._get_head_type())

        return ScrewParams(
            part_no=params.part_no,
            name=params.name,
            major_d=major_d,
            pitch=pitch,
            length=length,
            head_d=head_d,
            head_h=head_h,
            drive_type=self._get_drive_type(),
            head_type=self._get_head_type(),
            tail_type=self._get_tail_type(),
            hex_size=hex_size,
            socket_depth=iso.get("socket_depth", 2.5),
            cross_drive_size=cross_drive_size,
            gb_standard=lookup_gb_standard(self._get_head_type(), self._get_drive_type(), self._get_tail_type()),
        )

    def _enable_param_edit(self) -> None:
        """点击“调整”后，把参数框切换为可编辑，并填充最近一次识别结果."""
        if self._last_params is not None:
            self._set_params_from_model(self._last_params)
        for entry in self._param_entries.values():
            entry.config(state="normal")
        self._log("[调整模式] 参数框已解锁，可手动修改")

    def _reset_params_to_standard(self) -> None:
        """根据当前头型和螺纹大径，把参数重置为标准尺寸."""
        try:
            major_d = float(self.param_vars["major_d"].get().strip())
        except (ValueError, TypeError):
            self._log("[提示] 螺纹大径为空或非法，无法重置标准尺寸")
            return

        head_type = self._get_head_type()
        iso = lookup_iso(major_d, head_type)
        self.param_vars["pitch"].set(str(default_pitch(major_d)))
        self.param_vars["head_d"].set(str(iso["head_d"]))
        self.param_vars["head_h"].set(str(iso["head_h"]))
        if head_type == "socket":
            self.param_vars["hex_size"].set(str(iso.get("hex", 4.0)))
        else:
            self.param_vars["hex_size"].set(str(get_cross_drive_size(major_d)))
        self._log(f"[标准重置] M{major_d} {head_type} → head_d={iso['head_d']}, head_h={iso['head_h']}")

    def _auto_parse(self) -> None:
        """选择文件后自动解析参数."""
        path = self.input_path.get()
        if not path:
            return
        try:
            path_obj = Path(path)
            if path_obj.suffix.lower() in (".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".webp"):
                from .image_parser import extract_text_from_image
                raw_text = extract_text_from_image(path_obj)
                self._log(f"[OCR 原始文本]\n{raw_text.strip()}")
                params = parse_image(path_obj)
            else:
                params = parse_pdf(path_obj)
            self._last_params = params
            self._set_head_type(params.head_type)
            self._set_drive_type(params.drive_type)
            self._set_tail_type(params.tail_type)
            self._set_params_from_model(params)
            # 新文件解析后，参数框恢复只读，需要点击“调整”才能改
            for entry in self._param_entries.values():
                entry.config(state="readonly")
            self._set_result(str(params))
            self._log(f"[解析成功] {params.part_no} {params.name}")
        except Exception as exc:  # noqa: BLE001
            self._log(f"[解析失败] {exc}")
            messagebox.showerror("解析失败", str(exc))

    def _parse_input(self) -> None:
        """兼容旧的手动解析入口."""
        self._auto_parse()

    def _generate_step(self) -> None:
        path = self.input_path.get()
        out = self.out_dir.get()
        if not path:
            messagebox.showwarning("提示", "请先选择输入文件")
            return
        if not out:
            messagebox.showwarning("提示", "请先选择输出目录")
            return

        self.progress.start()

        def worker() -> None:
            try:
                path_obj = Path(path)
                if path_obj.suffix.lower() in (".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".webp"):
                    params = parse_image(path_obj)
                else:
                    params = parse_pdf(path_obj)
                # 合并用户手动修正
                params = self._build_params_from_model(params)
                out_path = generate_step(params, Path(out))
                self.root.after(0, lambda: self._set_result(str(params)))
                self.root.after(0, lambda: self._set_params_from_model(params))
                self.root.after(0, lambda: self._log(f"[生成成功] {out_path}"))
                self.root.after(0, lambda: messagebox.showinfo("完成", f"已生成 STEP 文件：\n{out_path}"))
            except Exception as exc:  # noqa: BLE001
                self.root.after(0, lambda: self._log(f"[生成失败] {exc}"))
                self.root.after(0, lambda: messagebox.showerror("生成失败", str(exc)))
            finally:
                self.root.after(0, self.progress.stop)

        threading.Thread(target=worker, daemon=True).start()

    def run(self) -> None:
        self.root.mainloop()


def main() -> None:
    app = StdPartsAIApp()
    app.run()
