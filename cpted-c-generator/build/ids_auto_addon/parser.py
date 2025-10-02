"""
IDS cache parser module (Jinja2 template).

This module is rendered by the generator to provide functions for loading
and querying the IDS requirement cache at runtime. It first attempts
to load a baked-in cache (cache_embedded.py) and falls back to the
ids_cache.json file in this module's directory. This approach avoids
relying on external data files when the add-on is packaged and makes
UI rendering more robust.
"""

import os
import json

# Attempt to import a baked-in cache. When present, this CACHE dict
# contains the parsed IDS requirements at build time.
try:
    from .cache_embedded import CACHE as _EMBEDDED
except Exception:
    _EMBEDDED = None


def _cache_path() -> str:
    """
    Return the path to the ids_cache.json file bundled alongside this module.
    """
    return os.path.join(os.path.dirname(__file__), "ids_cache.json")


def load_cache() -> dict:
    """
    Load the IDS cache dictionary.

    The loader tries the embedded cache first (if available) and falls
    back to reading ids_cache.json from disk. If neither exists,
    a stub dict with an empty requirements list is returned.
    """
    # Embedded cache takes precedence; it is baked in at build time.
    if _EMBEDDED is not None:
        return _EMBEDDED
    p = _cache_path()
    if not os.path.exists(p):
        return {"version": 1, "requirements": []}
    with open(p, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except Exception:
            return {"version": 1, "requirements": []}


def list_requirements() -> list:
    """
    Return the list of requirement dictionaries from the cache.
    """
    c = load_cache()
    return c.get("requirements", [])


def get_prop_config_by_key(key: str) -> dict | None:
    """
    Find and return the requirement definition corresponding to a given key.

    Parameters
    ----------
    key : str
        The composite key in the form "Object.Pset.Property".

    Returns
    -------
    dict or None
        The requirement dictionary if found, otherwise None.
    """
    for r in list_requirements():
        if r.get("key") == key:
            return r
    return None