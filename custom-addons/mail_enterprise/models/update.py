# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api
from odoo.models import AbstractModel
from odoo.tools import cloc

class PublisherWarrantyContract(AbstractModel):
    _inherit = "publisher_warranty.contract"

    @api.model
    def _get_message(self):
        msg = super()._get_message()

        ICP = self.env["ir.config_parameter"]
        if ICP.get_param('publisher_warranty.maintenance_disable') is not False:
            return msg

        msg['maintenance'] = {
            "version": cloc.VERSION,
        }
        try:
            c = cloc.Cloc()
            c.count_env(self.env)
            if c.code:
                msg["maintenance"]["modules"] = c.code
            if c.errors:
                msg["maintenance"]["errors"] = list(c.errors.keys())
        except Exception:
            msg["maintenance"]["errors"] = ['cloc/error']

        ICP.set_param('publisher_warranty.cloc', str(msg['maintenance']))
        return msg

    @api.model
    def _get_verbose_maintenance(self):
        """ can be called by a SA to debug cloc issue
            Without runing odoo-bin cloc which is not always possible
        """
        c = cloc.Cloc()
        c.count_env(self.env)
        return {
            "modules_count": c.modules,
            "modules_excluded": c.excluded,
        }
