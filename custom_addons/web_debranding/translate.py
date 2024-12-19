# Copyright 2022-2023 Ivan Yelizariev <https://twitter.com/yelizariev>
# License OPL-1 (https://www.odoo.com/documentation/user/14.0/legal/licenses/licenses.html#odoo-apps)
import inspect
import logging
import types

import odoo
from odoo.tools.translate import _

from .models.ir_translation import debrand

_logger = logging.getLogger(__name__)

_get_translation_original = _._get_translation


def _get_translation(self, source, module=None):
    source = _get_translation_original(source, module)

    frame = inspect.currentframe().f_back.f_back
    try:
        (cr, dummy) = _._get_cr(frame, allow_create=False)
    except AttributeError:
        return source
    try:
        uid = self._get_uid(frame)
    except Exception:
        return source
    if cr and uid:
        env = odoo.api.Environment(cr, uid, {})
        source = debrand(env, source)

    return source


_._get_translation = types.MethodType(_get_translation, _)
