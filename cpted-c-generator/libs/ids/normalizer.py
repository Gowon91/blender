# normalizer.py
"""
Normalizer for IDS requirement dictionaries.

This module contains helper functions used by the IDS add-on generator
and related utilities. It normalizes method names (e.g. A/B/C/D → lowercase)
and builds canonical keys for properties using the object, pset, and
property names from a parsed IDS cache.
"""

from typing import Dict, List

def normalize_method(method: str) -> str:
    """
    Normalize a method identifier to lowercase and strip whitespace.

    If the input is None or empty, an empty string is returned.

    Parameters
    ----------
    method : str
        The method identifier (e.g. "A", "b", "c").

    Returns
    -------
    str
        The method in lowercase. Returns an empty string if input is falsy.
    """
    if not method:
        return ""
    return method.lower().strip()

def build_key(requirement: Dict) -> str:
    """
    Construct the canonical key for a requirement.

    Given a requirement dictionary (as produced by the generator), this
    function returns a dot-separated string "Object.Pset.Property" if
    all components are present. Otherwise, it simply returns the property
    name. Keys are used to identify requirements uniquely when populating
    Blender custom properties.

    Parameters
    ----------
    requirement : dict
        A dictionary containing at least 'object', 'pset', and 'property' keys.

    Returns
    -------
    str
        The computed key.
    """
    obj = (requirement.get("object") or "").strip()
    pset = (requirement.get("pset") or "").strip()
    prop = (requirement.get("property") or "").strip()
    if obj and pset and prop:
        return f"{obj}.{pset}.{prop}"
    return prop

def normalize_requirement(req: Dict) -> Dict:
    """
    Normalize a single requirement dictionary in-place.

    This helper ensures the method is lowercase and populates the 'key'
    field if it is missing or empty. It returns the same dictionary for
    convenience.

    Parameters
    ----------
    req : dict
        The requirement dictionary to normalize.

    Returns
    -------
    dict
        The normalized requirement dictionary (same object).
    """
    req["method"] = normalize_method(req.get("method", ""))
    key = req.get("key", "").strip()
    if not key:
        req["key"] = build_key(req)
    return req

def normalize_requirements(reqs: List[Dict]) -> List[Dict]:
    """
    Normalize a list of requirement dictionaries.

    Applies normalize_requirement() to each element.

    Parameters
    ----------
    reqs : list of dict
        The list of requirements to normalize.

    Returns
    -------
    list of dict
        The list of normalized requirement dictionaries.
    """
    return [normalize_requirement(r) for r in reqs]