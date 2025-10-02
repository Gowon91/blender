# -*- coding: utf-8 -*-
"""
methods.py (템플릿)

역할:
    IDS Property 의 method 값(a/b/c/d)에 따라 자동 채움 로직을 제공한다.
    b 유형에 대해 ifcopenshell을 적극 활용하여 치수를 계산하며, 대체 경로로
    Blender 내장 bounding_box/dimensions 정보를 사용한다.

구현 개요:
    - method_a_manual(): A(수동) → 아무 값도 채우지 않는다.
    - method_b_geometry(): B(지오메트리 기반) → axis 혹은 slope 모드로 계산한다.
      * axis 모드: 해당 객체의 월드 AABB 치수를 가져와 Z축 등 지정된 축의 길이를
        반환한다. IFC 모델과 Blender 객체를 모두 활용하여 정확도를 높인다.
      * slope 모드: AABB 근사를 이용한 경사 계산(dz/run). 추후 ifcopenshell
        geometry 분석으로 개선할 수 있다.
    - method_c_relation(), method_d_simulation(): C/D는 범위 밖으로 빈 구현만 제공한다.

참고:
    • IFC 형상이 존재하는 경우 ifcopenshell.geom.create_shape() 로 삼각형 메쉬를
      생성하여 bounding box를 계산한다. USE_WORLD_COORDS 옵션을 사용하여 IFC
      엔티티의 월드 좌표를 얻는다. 필요에 따라 IDS_IFC_FILE 환경 변수를
      설정해야 한다.
    • Blender 오브젝트는 기본적으로 오브젝트의 bound_box (로컬 좌표 8점)와
      matrix_world 변환을 이용해 bounding box를 계산한다.
"""

import bpy
from math import sqrt
from mathutils import Vector

from . import parser

# 시도: ifcopenshell 임포트
_IFC = None
try:
    import ifcopenshell
    import ifcopenshell.geom
    _IFC = ifcopenshell
except Exception:
    _IFC = None

# ---------------------------
# IFC 기반 bounding box 계산
# ---------------------------

def _ifc_world_bbox_dims(elem):
    """
    IFC 엔티티의 월드 좌표계 기준 bounding box 크기(dx, dy, dz)를 계산한다.
    - ifcopenshell 이 설치되어 있어야 하며, elem 이 None 이 아니어야 한다.
    - 실패 시 (0,0,0)을 반환한다.
    """
    if not _IFC or elem is None:
        return (0.0, 0.0, 0.0)
    try:
        # geometry settings: world coords true
        settings = ifcopenshell.geom.settings()
        settings.set(settings.USE_WORLD_COORDS, True)
        shape = ifcopenshell.geom.create_shape(settings, elem)
        verts = shape.geometry.verts  # flat list [x0,y0,z0, x1,y1,z1, ...]
        xs = verts[0::3]
        ys = verts[1::3]
        zs = verts[2::3]
        # compute min/max
        dx = max(xs) - min(xs) if xs else 0.0
        dy = max(ys) - min(ys) if ys else 0.0
        dz = max(zs) - min(zs) if zs else 0.0
        # 메모리 해제
        del shape
        return (abs(dx), abs(dy), abs(dz))
    except Exception:
        return (0.0, 0.0, 0.0)


# ---------------------------
# Blender 오브젝트 기반 bounding box 계산
# ---------------------------

def _blender_world_bbox_dims(obj):
    """
    Blender 오브젝트의 월드 기준 AABB 크기(dx, dy, dz)를 계산한다.
    - obj.bound_box는 로컬 좌표의 8점을 제공하므로, matrix_world로 변환 후
      x/y/z 범위를 계산한다.
    - 실패 시 obj.dimensions를 사용한다.
    """
    try:
        coords = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
        xs = [c.x for c in coords]; ys = [c.y for c in coords]; zs = [c.z for c in coords]
        dx = max(xs) - min(xs) if xs else 0.0
        dy = max(ys) - min(ys) if ys else 0.0
        dz = max(zs) - min(zs) if zs else 0.0
        return (abs(dx), abs(dy), abs(dz))
    except Exception:
        try:
            d = obj.dimensions
            return (abs(float(d.x)), abs(float(d.y)), abs(float(d.z)))
        except Exception:
            return (0.0, 0.0, 0.0)


def _get_world_bbox_dims(obj):
    """
    주어진 Blender 오브젝트에 대해 IFC 기반 bbox → Blender bbox 순으로 반환한다.
    - parser.get_ifc_element() 을 통해 IFC 엔티티를 찾고, ifcopenshell.geom 으로 bbox를 구한다.
    - IFC 가 없거나 실패하면 Blender 오브젝트의 bbox를 사용한다.
    """
    elem = parser.get_ifc_element(obj)
    if elem is not None:
        dims = _ifc_world_bbox_dims(elem)
        if any(dims):  # 하나라도 0이 아니면 사용
            return dims
    return _blender_world_bbox_dims(obj)


# ---------------------------
# method별 구현
# ---------------------------

def method_a_manual(obj, key):
    """A: 수동 입력이므로 아무 것도 하지 않고 None을 반환한다."""
    return None


def _compute_axis_value(obj, bcfg):
    """
    axis 모드 계산: 지정된 축 길이를 스케일/반올림하여 반환한다.
    - bcfg: {source, axis, scale, precision, ...}
    - source: 'bbox' | 'dims' (여기서는 의미 없음, 항상 bounding box 사용)
    - axis: 'X'|'Y'|'Z'
    - scale: float (단위 환산)
    - precision: int (반올림 자릿수)
    """
    dims = _get_world_bbox_dims(obj)
    # axis 지정
    axis = (bcfg.get("axis") or "Z").upper()
    val = dims[2]  # 기본 Z
    if axis == "X":
        val = dims[0]
    elif axis == "Y":
        val = dims[1]
    # 스케일 및 반올림 적용
    scale = float(bcfg.get("scale") or 1.0)
    precision = int(bcfg.get("precision") or 2)
    try:
        val = round(val * scale, precision)
    except Exception:
        val = val * scale
    return val


def _compute_slope_value(obj, bcfg):
    """
    slope 모드 계산: bounding box를 이용한 근사 경사.
    - rise_axis: 경사로의 높이 축('X','Y','Z')
    - run_plane: 경사로의 수평 평면('XY','YZ','XZ')
    - scale: 곱해질 상수(예: 100 → %)
    - precision: 반올림 자릿수
    """
    dims = _get_world_bbox_dims(obj)
    rise_axis = (bcfg.get("rise_axis") or "Z").upper()
    run_plane = (bcfg.get("run_plane") or "XY").upper()
    # rise
    if rise_axis == "X":
        rise = dims[0]
    elif rise_axis == "Y":
        rise = dims[1]
    else:
        rise = dims[2]
    # run
    if run_plane == "YZ":
        run = sqrt(dims[1] ** 2 + dims[2] ** 2)
    elif run_plane == "XZ":
        run = sqrt(dims[0] ** 2 + dims[2] ** 2)
    else:
        run = sqrt(dims[0] ** 2 + dims[1] ** 2)
    slope_raw = rise / run if run > 1e-9 else 0.0
    scale = float(bcfg.get("scale") or (bcfg.get("precision") or 1.0))
    precision = int(bcfg.get("precision") or 2)
    try:
        val = round(slope_raw * scale, precision)
    except Exception:
        val = slope_raw * scale
    return val


def method_b_geometry(obj, key):
    """
    B: 지오메트리 기반 자동채움. axis 또는 slope 모드에 따라 값을 계산한다.
    - parser.get_prop_config_by_key() 에서 bcfg를 추출하여 모드 결정.
    """
    cfg = parser.get_prop_config_by_key(key) or {}
    bcfg = cfg.get("b", {}) if isinstance(cfg, dict) else {}
    compute = (bcfg.get("compute") or "axis").lower()
    if compute == "slope":
        return _compute_slope_value(obj, bcfg)
    # 기본 axis
    return _compute_axis_value(obj, bcfg)


def method_c_relation(obj, key):
    """
    C: 관계 기반 채움. 본 프로젝트 범위에서 구현하지 않는다.
    """
    return None


def method_d_simulation(obj, key):
    """
    D: 시뮬레이션/외부 연동 기반 채움. 본 프로젝트 범위에서 구현하지 않는다.
    """
    return None


# 디스패처: method 태그에서 함수 매핑
HANDLERS = {
    "a": method_a_manual,
    "b": method_b_geometry,
    "c": method_c_relation,
    "d": method_d_simulation,
}


def autofill_value(obj, method_tag, key):
    """
    주어진 method_tag(a/b/c/d)에 따라 값을 계산하여 반환한다.
    - obj: Blender 오브젝트
    - method_tag: 소문자 문자열
    - key: "Pset.Property" 문자열
    값이 계산되지 않으면 None을 반환한다.
    """
    fn = HANDLERS.get((method_tag or "a").lower())
    return fn(obj, key) if fn else None
