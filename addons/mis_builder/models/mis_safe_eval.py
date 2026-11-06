# Copyright 2016 ACSONE SA/NV (<http://acsone.eu>)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import traceback

from odoo.tools.safe_eval import _BUILTINS, _SAFE_OPCODES, test_expr

from .data_error import DataError, NameDataError

__all__ = ["mis_safe_eval"]


def mis_safe_eval(expr, locals_dict):
    """Evaluate an expression using safe_eval

    Returns the evaluated value or DataError.

    Raises NameError if the evaluation depends on a variable that is not
    present in local_dict.
    """
    try:
        c = test_expr(expr, _SAFE_OPCODES, mode="eval")
        globals_dict = {"__builtins__": _BUILTINS}
        # pylint: disable=eval-used,eval-referenced
        val = eval(c, globals_dict, locals_dict)
    except NameError:
        val = NameDataError("#NAME", traceback.format_exc())
    except ZeroDivisionError:
        # pylint: disable=redefined-variable-type
        val = DataError("#DIV/0", traceback.format_exc())
    except Exception:
        val = DataError("#ERR", traceback.format_exc())
    return val
