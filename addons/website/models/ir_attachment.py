# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import openerp
from openerp.osv import osv, fields


class ir_attachment(osv.osv):
    _inherit = "ir.attachment"

    _columns = {
        'website_url': fields.related("local_url", string="Attachment URL", type='char', deprecated=True), # related for backward compatibility with saas-6
    }
