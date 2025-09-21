# -*- coding: utf-8 -*-
"""
parser.py (템플릿)

역할:
    - ids_cache.json을 로드하여 meta와 requirements를 제공한다.
    - IFC 파일 연동을 위한 헬퍼 함수를 제공한다.
    - Blender 오브젝트를 IFC 엔티티와 매칭해 요구사항을 가져오는 기능을 포함한다.

주요 특징:
    • ids_cache.json 은 애드온 폴더의 루트에 위치하며, 이 모듈에서 단일하게 로드한다.
    • ifcopenshell 이 설치되어 있고 환경 변수 IDS_IFC_FILE 가 지정된 경우, IFC 모델을
      열어 오브젝트의 GlobalId 로 IFC 엔티티를 찾는다. 이름 매칭보다 우선한다.
    • iter_requirements_for_object() 는 먼저 IFC 타입 매칭을 시도하고, 실패하면 이름
      매칭을 수행한다.

주의:
    - Blender 에서 커스텀 프로퍼티로 Ifc 엔티티의 GlobalId 가 "GlobalId" 혹은
      "IfcGUID" 등 키로 저장되어 있다고 가정한다. 없으면 이름 매칭으로 대체한다.
    - ifcopenshell 설치가 필수가 아니므로, ImportError 발생 시 IFC 관련 기능은
      무시한다.
"""

import os
import json
import bpy

# ids_cache.json 경로 설정: 애드온 파일과 동일 디렉터리에 위치한다
BASE_DIR = os.path.dirname(__file__)
CACHE_JSON = os.path.join(BASE_DIR, "ids_cache.json")

# 캐시 데이터 로드 함수
_CACHE_DATA = None

def load_cache():
    """ids_cache.json을 로드하여 딕셔너리로 반환한다. 내부 캐시를 사용한다."""
    global _CACHE_DATA
    if _CACHE_DATA is None:
        with open(CACHE_JSON, "r", encoding="utf-8") as f:
            _CACHE_DATA = json.load(f)
    return _CACHE_DATA


def load_requirements():
    """ids_cache.json에서 requirements 목록을 반환한다."""
    return load_cache().get("requirements", [])


# IFC 연동을 위한 전역 객체: 모델은 한 번만 로드한다
_IFC_MODEL = None

def _try_import_ifcopenshell():
    """ifcopenshell 임포트 시도 후 반환한다. 실패하면 None."""
    try:
        import ifcopenshell
        return ifcopenshell
    except Exception:
        return None


def get_ifc_model():
    """
    환경 변수 IDS_IFC_FILE 로 지정된 IFC 파일을 열어 반환한다.
    - ifcopenshell 이 설치되지 않았거나 파일 경로가 없으면 None.
    - 모델은 캐시되어 여러 번 열지 않는다.
    """
    global _IFC_MODEL
    if _IFC_MODEL is not None:
        return _IFC_MODEL
    ifc_path = os.environ.get("IDS_IFC_FILE")
    if not ifc_path:
        return None
    # 임포트 시도
    ifc = _try_import_ifcopenshell()
    if not ifc:
        return None
    try:
        _IFC_MODEL = ifc.open(ifc_path)
    except Exception:
        _IFC_MODEL = None
    return _IFC_MODEL


def get_ifc_element(obj):
    """
    Blender 오브젝트의 GlobalId 커스텀 프로퍼티를 이용해 IFC 엔티티를 찾는다.
    - obj['GlobalId'], obj['IfcGUID'], obj['GlobalID'] 등의 키를 검사한다.
    - IDS_IFC_FILE 환경 변수가 지정되고 ifcopenshell 임포트에 성공해야 한다.
    - 찾은 엔티티 객체를 반환하고, 실패하면 None.
    """
    model = get_ifc_model()
    if not model:
        return None
    # 여러 키 중 하나라도 있으면 해당 GUID 사용
    guid = None
    for key in ("GlobalId", "IfcGUID", "GlobalID", "ifc_guid", "IFC_GUID"):
        try:
            val = obj.get(key)
            if isinstance(val, str) and val:
                guid = val
                break
        except Exception:
            continue
    if not guid:
        return None
    try:
        elem = model.by_guid(guid)
        return elem
    except Exception:
        return None


def _match_object_by_ifc(obj, req_object_label):
    """
    IFC 엔티티 타입으로 Requirement 객체 매칭을 수행한다.
    - obj 가 IFC 엔티티를 보유하고, 엔티티의 is_a() 메서드가 req_object_label
      (예: 'IfcFence') 를 만족하면 True.
    - req_object_label 가 비어있으면 항상 True.
    - ifcopenshell 가 없거나 IFC 엔티티를 찾지 못하면 False를 반환한다.
    """
    if not req_object_label:
        return True
    elem = get_ifc_element(obj)
    if not elem:
        return False
    try:
        # IfcOpenShell 엔티티는 is_a() 메서드를 제공한다
        return bool(elem.is_a(req_object_label))
    except Exception:
        return False


def _match_object_by_name(obj, req_object_label):
    """
    Blender 오브젝트 이름에 req_object_label 문자열이 포함되는지 검사한다.
    대소문자를 무시하며, req_object_label 이 비어있으면 True.
    """
    if not req_object_label:
        return True
    lo = (obj.name or "").lower()
    return req_object_label.lower() in lo


def iter_requirements_for_object(obj):
    """
    주어진 Blender 오브젝트에 해당하는 IDS 요구사항(Requirement)을 반복한다.
    - 먼저 IFC 엔티티를 통해 타입 매칭을 시도한다.
    - IFC 매칭이 실패하면 오브젝트 이름으로 매칭한다.
    """
    reqs = load_requirements()
    for req in reqs:
        obj_label = (req.get("object") or "").strip()
        # IFC 우선 매칭
        if _match_object_by_ifc(obj, obj_label):
            yield req
        # 이름 매칭(대소문자 무시)
        elif _match_object_by_name(obj, obj_label):
            yield req


def iter_pset_prop_keys_for_object(obj):
    """
    주어진 Blender 오브젝트와 매칭되는 모든 "Pset.Property" 키를 리스트로 반환한다.
    """
    keys = []
    for req in iter_requirements_for_object(obj):
        pset = req.get("pset") or ""
        for p in req.get("properties", []):
            pname = p.get("name")
            if pset and pname:
                keys.append(f"{pset}.{pname}")
    return keys
