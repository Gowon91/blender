"""
Method hooks for IDS add-on (Jinja2 template).

This module defines the mapping between method identifiers (a, b, c, d)
and the functions that implement them. For c-type methods, the heavy
lifting is handled in the ops module; here we simply return the
placeholder function for c.
"""

def get_method_fn(tag: str):
    """
    Return the callable associated with a method tag.

    Parameters
    ----------
    tag : str
        A single-character method identifier.

    Returns
    -------
    callable
        The function implementing the method; defaults to method_c.
    """
    tag = (tag or "c").lower().strip()
    # Currently, only c-types are supported; other methods may be added later.
    return method_c

def method_c(obj, key):
    """
    Placeholder method implementation for c-type requirements.

    The actual calculation of c-type relationships (distance_to, within)
    is performed in the ops module. This function exists solely as a
    dispatcher.

    Parameters
    ----------
    obj : bpy.types.Object
        The Blender object (unused in this stub).
    key : str
        The property key (unused in this stub).

    Returns
    -------
    None
    """
    return None