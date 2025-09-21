# validator.py
"""
Basic validation helpers for IDS XML documents.

This module defines a simple validation routine that can inspect an
ElementTree representing an IDS file and report missing or malformed
elements. It is intentionally lightweight and makes no attempt to fully
validate the IDS schema; instead, it focuses on common mistakes such as
missing Object/Pset/Property tags or invalid method attributes.
"""

import xml.etree.ElementTree as ET
from typing import List

VALID_METHODS = {"a", "b", "c", "d"}

def validate_ids(root: ET.Element) -> List[str]:
    """
    Validate the top-level IDS XML element.

    Parameters
    ----------
    root : xml.etree.ElementTree.Element
        The root element of an IDS document.

    Returns
    -------
    list of str
        A list of error messages describing problems found. If the
        returned list is empty, the document passed the basic checks.
    """
    errors: List[str] = []
    for req in root.findall(".//Requirement"):
        rid = req.attrib.get("id", "<unknown>")
        obj = req.find("Object")
        pset = req.find("Pset")
        props = req.findall("Property")
        # Check for missing Object/Pset
        if obj is None or not (obj.text or "").strip():
            errors.append(f"Requirement '{rid}' missing Object element or value")
        if pset is None or not (pset.text or "").strip():
            errors.append(f"Requirement '{rid}' missing Pset element or value")
        # Check for at least one Property
        if not props:
            errors.append(f"Requirement '{rid}' missing Property definition")
            continue
        for prop in props:
            name = prop.attrib.get("name")
            if not name:
                errors.append(f"Property without name attribute in requirement '{rid}'")
            method = prop.attrib.get("method")
            if method and method.lower() not in VALID_METHODS:
                errors.append(
                    f"Invalid method '{method}' in property '{name}' (requirement '{rid}')"
                )
    return errors