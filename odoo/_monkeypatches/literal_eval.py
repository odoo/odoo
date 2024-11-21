# ruff: noqa: E402, PLC0415
# ignore import not at top of the file
import ast
import logging
import os

_logger = logging.getLogger(__name__)
orig_literal_eval = ast.literal_eval


def literal_eval(expr):
    # limit the size of the expression to avoid segmentation faults
    # the default limit is set to 100KiB
    # can be overridden by setting the ODOO_LIMIT_LITEVAL_BUFFER buffer_size_environment variable

    buffer_size = 102400
    buffer_size_env = os.getenv("ODOO_LIMIT_LITEVAL_BUFFER")

    if buffer_size_env:
        if buffer_size_env.isdigit():
            buffer_size = int(buffer_size_env)
        else:
            _logger.error("ODOO_LIMIT_LITEVAL_BUFFER has to be an integer, defaulting to 100KiB")

    if isinstance(expr, str) and len(expr) > buffer_size:
        raise ValueError("expression can't exceed buffer limit")

    return orig_literal_eval(expr)


def patch_literal_eval():
    ast.literal_eval = literal_eval
