"""
IDS loader utilities.

This module provides simple helper functions to load IDS (Information Delivery
Specification) files from XML. It returns either the root element of the
document or the entire ElementTree for further processing.
"""

import xml.etree.ElementTree as ET
from typing import Optional

def load_xml(path: str) -> ET.Element:
    """
    Load an IDS XML file and return its root element.

    Parameters
    ----------
    path : str
        Path to the IDS XML file.

    Returns
    -------
    xml.etree.ElementTree.Element
        The parsed root element of the IDS document.

    Raises
    ------
    xml.etree.ElementTree.ParseError
        If the XML is malformed.
    OSError
        If the file cannot be read.
    """
    tree = ET.parse(path)
    return tree.getroot()

def load_tree(path: str) -> ET.ElementTree:
    """
    Load and return the entire ElementTree for an IDS file.

    Parameters
    ----------
    path : str
        Path to the IDS XML file.

    Returns
    -------
    xml.etree.ElementTree.ElementTree
        The parsed ElementTree of the IDS document.
    """
    return ET.parse(path)