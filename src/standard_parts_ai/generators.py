# -*- coding: utf-8 -*-
"""CadQuery 螺丝几何生成与 STEP 导出."""

from pathlib import Path

import cadquery as cq

from .models import ScrewParams
from .standards import CROSS_DRIVE_TABLE, get_cross_drive_size


def _build_thread(params: ScrewParams) -> cq.Workplane:
    """构建螺杆（简化表示）：直接按螺纹大径圆柱生成，不生成真实牙型."""
    p = params
    # 头部与螺杆接触面做轻微重叠，避免小规格布尔并失败
    overlap = 0.05
    total_length = p.length + overlap
    return cq.Workplane("XY").circle(p.major_d / 2).extrude(total_length)


def _build_head_socket(params: ScrewParams) -> cq.Workplane:
    """内六角圆柱头."""
    head = (
        cq.Workplane("XY")
        .workplane(offset=params.length)
        .circle(params.head_d / 2)
        .extrude(params.head_h)
    )
    return head


def _build_head_pan(params: ScrewParams) -> cq.Workplane:
    """盘头：圆柱底座 + 浅球冠，更接近 ISO 7045 / DIN 7985 盘头形状."""
    r = params.head_d / 2
    h = params.head_h
    # 盘头顶部为浅球冠，高度不超过半径，约占头高的 20%~30%
    dome_h = min(h * 0.25, r)
    cyl_h = h - dome_h

    base = (
        cq.Workplane("XY")
        .workplane(offset=params.length)
        .circle(r)
        .extrude(cyl_h)
    )

    # 球冠：半径等于头半径，球心在圆柱顶面，与圆柱顶圆周相切
    sphere = cq.Workplane("XY").workplane(offset=params.length + cyl_h).sphere(r)
    clip = (
        cq.Workplane("XY")
        .workplane(offset=params.length + cyl_h + dome_h / 2)
        .box(params.head_d, params.head_d, dome_h, centered=True)
    )
    dome = sphere.intersect(clip)

    return base.union(dome)


def _build_head_round(params: ScrewParams) -> cq.Workplane:
    """圆头：按标准 head_h 生成球冠."""
    r = params.head_d / 2
    h = params.head_h
    # 球冠几何：已知底面半径 r、球冠高度 h，求球半径 R
    if h <= 0:
        # 退化情况，退化为半球
        R = r
    else:
        R = (r * r + h * h) / (2 * h)
    z_center = params.length + h - R

    sphere = cq.Workplane("XY").workplane(offset=z_center).sphere(R)
    clip = (
        cq.Workplane("XY")
        .workplane(offset=params.length + h / 2)
        .box(params.head_d, params.head_d, h, centered=True)
    )
    return sphere.intersect(clip)


def _build_head_countersunk(params: ScrewParams) -> cq.Workplane:
    """沉头：圆锥台，从杆顶外径 loft 到头外径."""
    r_major = params.major_d / 2
    r_head = params.head_d / 2

    # 在 XY 平面从 z=0 的杆外径 loft 到 z=head_h 的头外径，形成圆锥台
    head = (
        cq.Workplane("XY")
        .workplane(offset=0)
        .circle(r_major)
        .workplane(offset=params.head_h)
        .circle(r_head)
        .loft()
    )
    # 平移到螺杆顶面
    return head.translate((0, 0, params.length))


def _add_drive_hex(params: ScrewParams, head: cq.Workplane) -> cq.Workplane:
    """在头部添加内六角孔."""
    hex_diameter = params.hex_size / (3 ** 0.5 / 2)
    socket = (
        cq.Workplane("XY")
        .workplane(offset=params.length + params.head_h - params.socket_depth)
        .polygon(6, hex_diameter)
        .extrude(params.socket_depth + 0.1, combine=False)
    )
    return head.cut(socket)


def _add_drive_cross(params: ScrewParams, head: cq.Workplane) -> cq.Workplane:
    """在头部添加十字槽."""
    major_d = params.major_d
    cross_size = params.cross_drive_size or get_cross_drive_size(major_d)
    dims = CROSS_DRIVE_TABLE.get(cross_size, CROSS_DRIVE_TABLE["3"])
    slot_width = dims["width"]
    slot_depth = dims["depth"]

    # 槽长度按头部直径
    slot_length = params.head_d * 0.7
    # 槽深度不能超过头高，避免穿透头部
    slot_depth = min(slot_depth, max(params.head_h - 0.1, 0.05))

    # 两个垂直长方体形成十字
    slot1 = (
        cq.Workplane("XY")
        .workplane(offset=params.length + params.head_h - slot_depth)
        .box(slot_length, slot_width, slot_depth + 0.1, centered=False)
    )
    # 居中
    slot1 = slot1.translate((-slot_length / 2, -slot_width / 2, 0))

    slot2 = (
        cq.Workplane("XY")
        .workplane(offset=params.length + params.head_h - slot_depth)
        .box(slot_width, slot_length, slot_depth + 0.1, centered=False)
    )
    slot2 = slot2.translate((-slot_width / 2, -slot_length / 2, 0))

    head = head.cut(slot1)
    head = head.cut(slot2)
    return head


def _add_tail_flat(params: ScrewParams, body: cq.Workplane) -> cq.Workplane:
    """平尾：保持底面平整（尝试小倒角，失败则保留原样）."""
    try:
        return body.faces("<Z").chamfer(0.1)
    except Exception:  # noqa: BLE001
        return body


def _add_tail_sharp(params: ScrewParams, body: cq.Workplane) -> cq.Workplane:
    """尖尾：从螺纹大径开始逐渐变细成圆锥."""
    tip_length = max(params.major_d * 1.5, 1.0)
    if tip_length > params.length:
        tip_length = params.length * 0.5

    # 圆锥顶部与螺纹外径对齐，底部尖点
    cone = (
        cq.Workplane("XY")
        .workplane(offset=0)
        .circle(params.major_d / 2)
        .workplane(offset=-tip_length)
        .circle(0.001)
        .loft()
    )
    body = body.union(cone)
    return body


def build_screw(params: ScrewParams) -> cq.Workplane:
    """用 CadQuery 构建螺丝."""
    # 1. 螺杆 + 螺纹
    body = _build_thread(params)

    # 2. 头部
    head_builders = {
        "socket": _build_head_socket,
        "pan": _build_head_pan,
        "round": _build_head_round,
        "countersunk": _build_head_countersunk,
    }
    head_builder = head_builders.get(params.head_type, _build_head_socket)
    head = head_builder(params)

    # 3. 驱动槽
    if params.drive_type == "hex":
        head = _add_drive_hex(params, head)
    elif params.drive_type == "cross":
        head = _add_drive_cross(params, head)

    # 4. 组合头部和螺杆
    screw = body.union(head)

    # 5. 尾部处理
    if params.tail_type == "sharp":
        screw = _add_tail_sharp(params, screw)
    else:
        screw = _add_tail_flat(params, screw)

    return screw


def generate_step(params: ScrewParams, out_dir: Path) -> Path:
    """生成并导出 STEP 文件."""
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{params.part_no}.step"

    screw = build_screw(params)
    screw.val().exportStep(str(out_path))
    return out_path
