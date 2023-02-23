# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dataclasses import dataclass, field


@dataclass(frozen=True)
class AliasError:
    """Alias error description.

    Arguments:
        code (str): error code
        message (str): translated user message
        is_config_error (bool): whether the error was caused by a mis-configured alias or not
    """
    code: str
    message: str = field(default='', compare=False)
    is_config_error: bool = field(default=False, compare=False)
