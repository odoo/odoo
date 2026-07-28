# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

def __getattr__(name):
    # pylint: disable=import-outside-toplevel
    if name not in ('osv', 'osv_memory', 'osv_abstract', 'except_osv'):
        raise AttributeError(name)

    from ..exceptions import UserError
    from ..models import Model, TransientModel, AbstractModel

    import warnings

    target = Model if name == 'osv'\
        else UserError if name == 'except_osv'\
        else TransientModel if name == 'osv_memory'\
        else AbstractModel

    warnings.warn(
        f"Since 17.0: odoo.osv.osv.{name} is deprecated, use {target.__module__}.{target.__name__}",
        category=DeprecationWarning,
        stacklevel=2
    )
    return target
