# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import ast

from odoo.exceptions import ValidationError
from odoo.tools import is_list_of


def parse_res_ids(res_ids, env):
    """ Returns the already valid list/tuple of int or returns the literal eval
    of the string as a list/tuple of int. Void strings / missing values are
    evaluated as an empty list.

    :param str|tuple|list res_ids: a list of ids, tuple or list;

    :raise: ValidationError if the provided res_ids is an incorrect type or
      invalid format;

    :return list: list of ids
    """
    if is_list_of(res_ids, int) or not res_ids:
        return res_ids
    error_msg = env._(
        "Invalid res_ids %(res_ids_str)s (type %(res_ids_type)s)",
        res_ids_str=res_ids,
        res_ids_type=str(res_ids.__class__.__name__),
    )
    try:
        res_ids = ast.literal_eval(res_ids)
    except Exception as e:
        raise ValidationError(error_msg) from e

    if not is_list_of(res_ids, int):
        raise ValidationError(error_msg)

    return res_ids
