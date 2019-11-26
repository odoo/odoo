<<<<<<< HEAD
# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

=======
# coding: utf-8
>>>>>>> 8f3304ce601... temp
from odoo import models
from odoo.osv import expression


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    @classmethod
    def _get_translation_frontend_modules_domain(cls):
        domain = super(IrHttp, cls)._get_translation_frontend_modules_domain()
<<<<<<< HEAD
        return expression.OR([domain, [('name', '=', 'payment')]])
=======
        return expression.OR([domain, [('name', '=ilike', 'payment%')]])
>>>>>>> 8f3304ce601... temp
