# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (c) 2010 Camptocamp SA (http://www.camptocamp.com)
# Author : Nicolas Bessi (Camptocamp)

from openerp.osv import fields, osv

class res_company(osv.osv):
    """Override company to add Header object link a company can have many header and logos"""

    _inherit = "res.company"
    _columns = {
                'header_image' : fields.many2many(
                                                    'ir.header_img',
                                                    'company_img_rel',
                                                    'company_id',
                                                    'img_id',
                                                    'Available Images',
                                                ),
                'header_webkit' : fields.many2many(
                                                    'ir.header_webkit',
                                                    'company_html_rel',
                                                    'company_id',
                                                    'html_id',
                                                    'Available html',
                                                ),
    }
