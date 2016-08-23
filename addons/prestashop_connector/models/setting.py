# -*- coding: utf-8 -*-

from openerp.osv import orm, fields


class prestashop_config_settings(orm.TransientModel):
    _inherit = 'connector.config.settings'

    _columns = {
        'module_prestashopconnector_other_module': fields.boolean(
            "Example setting checkbox (experimental)",
            help="This installs the module prestashopconnector_... "
                 "(no real action now)"),
    }
