#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
generate_addon.py

본 스크립트는 IDS(XML) 정의 파일을 읽어 ids_cache.json을 생성하고, 템플릿 파일을
복사하여 Blender 애드온 폴더 구조를 만드는 역할을 수행한다. 특히 b 유형
(지오메트리 기반 자동 채움) 항목을 지원하도록 설계되었다.

동작 개요:
1. 사용자 지정 IDS XML을 파싱하여 meta 정보와 requirements 목록을 추출한다.
2. 파싱된 결과를 ids_cache.json으로 저장한다. 이 캐시가 애드온의 유일한 데이터
   소스로 사용되며, SSOT(Single Source of Truth) 원칙을 따른다.
3. generator/templates 디렉터리의 템플릿(.tpl.py) 파일을 복사하고,
   확장자를 .py로 변경하여 ids_auto_addon 폴더로 출력한다.

주요 주의 사항:
* method 값은 항상 소문자 a/b/c/d 로 정규화된다.
* b 유형에 대해서는 axis 모드와 slope 모드를 지원한다. slope 모드는 간단한
  AABB 근사치를 기반으로 경사를 계산하며, ifcopenshell 라이브러리가
  사용 가능한 경우 더 정확한 치수 추출에 활용될 수 있다.
* 검증/리포트/IFC 직접 쓰기는 포함하지 않는다. 애드온은 Pset.Property 생성과
  자동 채움(b)을 수행하는 것에 집중한다.

사용 예:
    cd generator
    python generate_addon.py --ids ./input/cpted_ids_b_baseline.xml --clean
    # 실행 후 ../ids_auto_addon/ 폴더가 생성된다. Blender에서 Add-on으로 로드 가능.

환경 변수:
* IDS_IFC_FILE: 선택 사항. b 유형 값 계산 시 ifcopenshell을 통해 IFC 형상을
  추출해야 할 경우, 해당 IFC 파일 경로를 지정할 수 있다. methods.tpl.py에서
  참조한다.

"""

import os
import sys
import json
import shutil
import argparse
import xml.etree.ElementTree as ET
from datetime import datetime

# 상수 정의: 현재 스크립트의 위치를 기준으로 경로를 계산한다.
HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(HERE, "templates")
DEFAULT_IDS = os.path.join(HERE, "input", "cpted_ids_b_baseline.xml")
DEFAULT_OUT = os.path.abspath(os.path.join(HERE, "..", "ids_auto_addon"))


def lname(tag: str) -> str:
    """네임스페이스가 있는 XML 태그에서 로컬명을 추출한다."""
    if tag and tag.startswith("{") and "}" in tag:
        return tag.split("}", 1)[1]
    return tag


def text_of(node: ET.Element) -> str:
    """요소의 모든 텍스트를 이어붙이고 공백을 정리해 반환한다."""
    if node is None:
        return None
    txt = "".join(node.itertext()).strip()
    return txt or None


def first_text(parent: ET.Element, candidates) -> str:
    """
    parent 하위 자식들 중에서 candidates 목록의 로컬 태그명과 일치하는 첫 번째
    자식의 텍스트를 반환한다. 없으면 None을 반환한다.
    """
    if parent is None:
        return None
    cset = {c.lower() for c in candidates}
    for ch in parent:
        if lname(ch.tag).lower() in cset:
            t = text_of(ch)
            if t:
                return t
    return None


def parse_number(val, kind="float", default=None):
    """
    문자열 숫자를 안전하게 파싱하여 float 또는 int를 반환한다.
    실패 시 default를 반환한다.
    """
    try:
        if val is None:
            return default
        s = str(val).strip()
        if kind == "int":
            return int(float(s))
        return float(s)
    except Exception:
        return default


def parse_ids(ids_path: str) -> dict:
    """
    IDS(XML)을 파싱하여 meta 정보와 requirements 목록을 포함하는 사전을 반환한다.
    - meta: schemaVersion, title, createdAt, locale
    - requirements: 각 Requirement 마다 object, pset, properties 배열을 포함
    - properties: name, method, dtype, unit, label, default, desc, group, order, readonly,
      b 구성(extract 설정)

    b 유형에 대해 axis/slope 모드를 지원하고, 기본값을 명시한다.
    """
    if not os.path.exists(ids_path):
        raise FileNotFoundError(f"IDS 파일이 존재하지 않는다: {ids_path}")

    tree = ET.parse(ids_path)
    root = tree.getroot()

    # meta 정보 추출: 속성값이 없으면 기본값 사용
    meta = {
        "schemaVersion": root.get("schemaVersion") or "1.0",
        "title": root.get("title") or "CPTED-IDS",
        "createdAt": root.get("createdAt") or datetime.now().strftime("%Y-%m-%dT%H:%M"),
        "locale": root.get("locale") or "ko-KR",
    }

    requirements = []
    for req in root.findall(".//*"):
        if lname(req.tag).lower() != "requirement":
            continue
        obj = first_text(req, ("Object", "object"))
        pset = first_text(req, ("Pset", "pset", "PropertySet", "propertyset", "property-set"))
        if not obj:
            raise ValueError("Requirement에 Object가 누락되었다.")
        if not pset:
            raise ValueError(f"Requirement(object={obj})에 Pset이 누락되었다.")

        props = []
        for p in req.findall(".//*"):
            if lname(p.tag).lower() != "property":
                continue

            name = (p.get("name") or "").strip()
            if not name:
                # name 태그 지원
                name = first_text(p, ("name", "basename", "propertyname", "property-name")) or ""
                name = name.strip()
            if not name:
                raise ValueError(f"Property name 누락 (object={obj}, pset={pset})")

            method = ((p.get("method") or "a").strip()).lower()
            if method not in {"a", "b", "c", "d"}:
                raise ValueError(f"지원하지 않는 method: {method} (Property: {name})")
            dtype = (p.get("dtype") or "").strip() or first_text(p, ("dtype", "datatype", "data-type", "type")) or ""
            unit = (p.get("unit") or "").strip() or first_text(p, ("unit", "uom", "measure")) or ""
            label = (p.get("label") or "").strip() or first_text(p, ("label",)) or ""
            desc = (p.get("desc") or "").strip() or first_text(p, ("desc", "description")) or ""
            # default 값: 숫자면 숫자, 아니면 문자열
            default_raw = p.get("default")
            if default_raw is None:
                default_raw = first_text(p, ("default",))
            default_val = None
            if default_raw is not None:
                try:
                    default_val = int(default_raw) if str(default_raw).isdigit() else float(default_raw)
                except Exception:
                    default_val = default_raw

            group = (p.get("group") or "").strip()
            order = parse_number(p.get("order"), kind="int", default=None)
            readonly = str(p.get("readonly") or "").strip().lower() in ("1", "true", "yes")

            prop = {
                "name": name,
                "method": method,
            }
            if dtype:
                prop["dtype"] = dtype
            if unit:
                prop["unit"] = unit
            if label:
                prop["label"] = label
            if desc:
                prop["desc"] = desc
            if default_val is not None:
                prop["default"] = default_val
            if group:
                prop["group"] = group
            if order is not None:
                prop["order"] = order
            if readonly:
                prop["readonly"] = True

            # b 모드 추가 파라미터
            if method == "b":
                # 기본값 초기화
                bcfg = {
                    "compute": "axis",
                    "source": "bbox",
                    "axis": "Z",
                    "scale": 1.0,
                    "precision": 2,
                    "rise_axis": "Z",
                    "run_plane": "XY",
                }
                # 자식 태그 우선 탐색
                def child_val(tag_names):
                    return first_text(p, tag_names)

                # axis/slope 모드
                compute = (child_val(("b_compute", "compute")) or p.get("b_compute") or "").strip()
                if compute:
                    bcfg["compute"] = compute.lower()

                source = (child_val(("b_source", "source")) or p.get("b_source") or "").strip()
                if source:
                    bcfg["source"] = source.lower()
                axis_val = (child_val(("b_axis", "axis")) or p.get("b_axis") or "").strip()
                if axis_val:
                    bcfg["axis"] = axis_val.upper()
                scale = child_val(("b_scale", "scale")) or p.get("b_scale")
                prec = child_val(("b_precision", "precision")) or p.get("b_precision")
                if scale is not None:
                    bcfg["scale"] = parse_number(scale, kind="float", default=bcfg["scale"])
                if prec is not None:
                    bcfg["precision"] = parse_number(prec, kind="int", default=bcfg["precision"])
                rise_axis = (child_val(("rise_axis", "b_rise_axis")) or p.get("rise_axis") or p.get("b_rise_axis") or "").strip()
                run_plane = (child_val(("run_plane", "b_run_plane")) or p.get("run_plane") or p.get("b_run_plane") or "").strip()
                if rise_axis:
                    bcfg["rise_axis"] = rise_axis.upper()
                if run_plane:
                    bcfg["run_plane"] = run_plane.upper()
                # 유효성 보정
                if bcfg["compute"] not in ("axis", "slope"):
                    bcfg["compute"] = "axis"
                if bcfg["axis"] not in ("X", "Y", "Z"):
                    bcfg["axis"] = "Z"
                if bcfg["source"] not in ("bbox", "dims"):
                    bcfg["source"] = "bbox"
                prop["b"] = bcfg

            # c/d 모드 자리만 유지; 파서는 추가 설정을 저장하지 않는다.
            props.append(prop)

        requirements.append({
            "object": obj,
            "pset": pset,
            "properties": props
        })

    return {"meta": meta, "requirements": requirements}


def ensure_dir(path: str) -> None:
    """디렉터리가 없으면 생성한다."""
    os.makedirs(path, exist_ok=True)


def write_ids_cache(cache: dict, out_dir: str) -> str:
    """ids_cache.json 파일을 지정한 폴더에 작성한다."""
    path = os.path.join(out_dir, "ids_cache.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)
    return path


def copy_templates(out_dir: str) -> None:
    """
    templates 디렉터리에 있는 .tpl.py 파일을 out_dir로 복사하여
    .py 확장자로 저장한다. 치환 변수가 필요하면 이 함수에서 구현한다.
    """
    mapping = {
        "__init__.tpl.py": "__init__.py",
        "parser.tpl.py": "parser.py",
        "methods.tpl.py": "methods.py",
        "ops.tpl.py": "ops.py",
        "ui.tpl.py": "ui.py",
    }
    if not os.path.isdir(TEMPLATES_DIR):
        raise FileNotFoundError(f"템플릿 폴더가 존재하지 않는다: {TEMPLATES_DIR}")
    for src_name, dst_name in mapping.items():
        src = os.path.join(TEMPLATES_DIR, src_name)
        if not os.path.exists(src):
            raise FileNotFoundError(f"템플릿 파일이 존재하지 않는다: {src}")
        dst = os.path.join(out_dir, dst_name)
        with open(src, "r", encoding="utf-8") as f_in, open(dst, "w", encoding="utf-8") as f_out:
            content = f_in.read()
            # 향후 치환이 필요하면 여기서 content.replace()를 사용한다.
            f_out.write(content)


def main():
    parser_cli = argparse.ArgumentParser(description="IDS → Blender 애드온 자동 생성기")
    parser_cli.add_argument("--ids", default=DEFAULT_IDS, help=f"IDS XML 경로 (기본: {DEFAULT_IDS})")
    parser_cli.add_argument("--out", default=DEFAULT_OUT, help=f"출력 애드온 폴더 경로 (기본: {DEFAULT_OUT})")
    parser_cli.add_argument("--clean", action="store_true", help="출력 폴더를 덮어쓰기 전에 삭제한다")
    args = parser_cli.parse_args()

    ids_path = os.path.abspath(args.ids)
    out_dir = os.path.abspath(args.out)

    print("=== IDS → 애드온 생성을 시작한다 ===")
    print(f"IDS 파일: {ids_path}")
    print(f"출력 폴더: {out_dir}")
    print(f"템플릿 폴더: {TEMPLATES_DIR}")

    # 1) IDS 파싱
    try:
        cache = parse_ids(ids_path)
    except Exception as e:
        print(f"[에러] IDS 파싱 실패: {e}")
        sys.exit(1)

    # 2) 출력 폴더 준비
    if os.path.exists(out_dir):
        if args.clean:
            print("기존 출력 폴더를 삭제한다 (--clean 옵션)")
            shutil.rmtree(out_dir)
        else:
            print("기존 출력 폴더가 존재한다. 내용을 덮어쓴다.")
    ensure_dir(out_dir)

    # 3) 템플릿 복사
    try:
        copy_templates(out_dir)
    except Exception as e:
        print(f"[에러] 템플릿 복사 실패: {e}")
        sys.exit(1)

    # 4) ids_cache.json 작성
    try:
        cache_path = write_ids_cache(cache, out_dir)
    except Exception as e:
        print(f"[에러] ids_cache.json 생성 실패: {e}")
        sys.exit(1)

    # 5) 완료 정보 출력
    req_count = len(cache.get("requirements", []))
    prop_count = sum(len(r.get("properties", [])) for r in cache.get("requirements", []))

    print("=== 애드온 생성 완료 ===")
    print(f"meta.title: {cache.get('meta', {}).get('title')}")
    print(f"Requirements 수: {req_count}")
    print(f"Properties 총 수: {prop_count}")
    print(f"애드온 폴더: {out_dir}")
    print(f"캐시 파일: {cache_path}")
    print("\n다음 단계:")
    print("1) 위 폴더(ids_auto_addon)를 Blender 애드온 경로에 복사한다.")
    print("2) Blender > Edit > Preferences > Add-ons 에서 애드온을 활성화한다.")
    print("3) View3D > Sidebar > IDS 패널에서 [속성 생성], [자동채움 실행]을 사용한다.")
    print("\n참고:")
    print("* 본 애드온은 b 유형(지오메트리)만 자동채움을 제공한다. A는 수동 입력이다.")
    print("* 검증·리포트·IFC 직접 쓰기는 포함하지 않는다.")
    print("* IDS를 수정한 경우, 본 스크립트를 다시 실행하여 캐시와 애드온을 갱신한다.")


if __name__ == "__main__":
    main()