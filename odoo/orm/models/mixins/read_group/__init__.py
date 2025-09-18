"""
Read group operations sub-package.

Split from the original 72KB read_group.py monolith into focused modules:
- sql.py: SQL generation (SELECT, GROUP BY, HAVING, ORDER BY)
- format.py: Post-processing and result formatting
- fill.py: Fill/expansion for empty groups and temporal gaps
- mixin.py: Main ReadGroupMixin with entry points (_read_group, read_group)

READ_GROUP_* constants live in ``odoo.orm.constants``.
"""

from .mixin import ReadGroupMixin

__all__ = ["ReadGroupMixin"]
