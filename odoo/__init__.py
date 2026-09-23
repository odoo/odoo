from typing import TYPE_CHECKING, Any

__all__ = ["SUPERUSER_ID", "Command", "_", "_lt", "evented"]

evented: bool = False

if TYPE_CHECKING:
    from odoo.orm.primitives import SUPERUSER_ID as SUPERUSER_ID
    from odoo.orm.primitives import Command as Command
    from odoo.tools.translate import _ as _
    from odoo.tools.translate import _lt as _lt


def __getattr__(name: str) -> Any:
    if name in ("SUPERUSER_ID", "Command"):
        from odoo.orm import primitives

        return getattr(primitives, name)
    if name in ("_", "_lt"):
        from odoo.tools import translate

        return getattr(translate, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
