"""Reset CPython's per-type version-tag budget (Python >= 3.13).

Since 3.13, a class that consumed MAX_VERSIONS_PER_CLASS (1000) version tags has its attribute cache disabled permanently
(see CPython https://github.com/python/cpython/pull/114900)
Every attribute access then falls back to an uncached MRO walk.

reset_classes_tp_versions_used allows to reset the tp_versions_used of every exhausted class (or close to be exhausted depending on reset_above_ratio)
in the models MROs, so that the attribute cache is re-enabled.
"""
import ctypes
import logging
import sys

assign_version_tag = ctypes.pythonapi.PyUnstable_Type_AssignVersionTag
assign_version_tag.argtypes = [ctypes.py_object]
assign_version_tag.restype = ctypes.c_int

_logger = logging.getLogger(__name__)

_warned = set()

__all__ = ["reset_classes_tp_versions_used"]


MAX_VERSIONS_PER_CLASS = 1000  # defined in cpython


def _detect_tp_versions_used_offset():
    """
    Automatically detect the offset of the `tp_versions_used` on the class
    The expected value is 410 in python 3.13 and 3.14 on 64bit platforms, but it may change in future versions or on other platforms
    This logics tries to find the offset dynamically by scanning the memory of a class that has exhausted its version tag budget
    This may break silently if MAX_VERSIONS_PER_CLASS is increased over 1000
    """

    class TestObject:
        ...

    for i in range(MAX_VERSIONS_PER_CLASS + 10):
        TestObject.x = i
        assign_version_tag(TestObject)

    if not assign_version_tag(TestObject):
        assert type.__basicsize__ > 0
        data = ctypes.string_at(id(TestObject), type.__basicsize__)
        max_version_per_class = bytes(ctypes.c_uint16(MAX_VERSIONS_PER_CLASS))  # tp_versions_used value once exhausted
        b_0 = bytes(ctypes.c_uint16(0))  # tp_versions_used value for reset
        for off in range(len(data) - 1):
            if data[off:off + 2] == max_version_per_class:
                ctypes.memmove(id(TestObject) + off, b_0, 2)  # 2 bytes: tp_versions_used is a uint16_t
                if assign_version_tag(TestObject):  # revived worked
                    _logger.info("Detected tp_versions_used at offset %d, reset enabled", off)
                    return off
                ctypes.memmove(id(TestObject) + off, max_version_per_class, 2)  # restore to original value to 1000 since it was most likely not the right offset
        _logger.warning("Could not detect tp_versions_used offset, the attribute cache will not be reset")
    elif sys.version_info >= (3, 13):
        _logger.warning('Failed to exhaust class version tags in python %s using %s iterations', sys.version_info, MAX_VERSIONS_PER_CLASS + 10)
    return None


_tp_versions_used_offset = ...


def get_tp_versions_used_offset():
    """
    lazily define tp_versions_used_offset
    """
    global _tp_versions_used_offset  # noqa: PLW0603
    if _tp_versions_used_offset == ...:
        _tp_versions_used_offset = _detect_tp_versions_used_offset()
    return _tp_versions_used_offset


def reset_classes_tp_versions_used(classes, reset_above_ratio=1):
    """
    Set to 0 the tp_versions_used of every exhausted class in the classes MROs (or close to be exhausted depending on reset_above_ratio)
    """
    tp_versions_used_offset = get_tp_versions_used_offset()
    if tp_versions_used_offset is None:
        return
    base_classes = dict.fromkeys(c for model_cls in classes for c in reversed(model_cls.__mro__))
    b_0 = bytes(ctypes.c_uint16(0))  # tp_versions_used value for reset
    for cls in base_classes:
        used = ctypes.c_int16.from_address(id(cls) + tp_versions_used_offset).value
        if used > MAX_VERSIONS_PER_CLASS:
            # we expect the max value to be MAX_VERSIONS_PER_CLASS (1000), if higher the cache was disabled for correctness and must never be re-enabled
            # https://github.com/python/cpython/issues/127773
            if repr(cls) not in _warned:
                _warned.add(repr(cls))
                _logger.warning("could not reset version tag budget of %r: the cache was permanently disabled by CPython", cls)
            continue
        if (MAX_VERSIONS_PER_CLASS * reset_above_ratio) <= used:
            ctypes.memmove(id(cls) + tp_versions_used_offset, b_0, 2)
    for cls in base_classes:
        # Note: this call to assign_version_tag is not only a check, it will also ensure that we have a tag assigned on a class that was already exhausted
        if not assign_version_tag(cls) and repr(cls) not in _warned:
            _warned.add(repr(cls))
            _logger.warning("could not reset version tag budget of %r", cls)
