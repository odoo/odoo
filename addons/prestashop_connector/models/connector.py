# -*- coding: utf-8 -*-
from openerp.osv import orm


class prestashopconnector_installed(orm.AbstractModel):
    """Empty model used to know if the module is installed in the
    database.

    If the model is in the registry, the module is installed.
    """
    _name = 'prestashopconnector.installed'
