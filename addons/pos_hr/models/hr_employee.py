# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import hashlib

from odoo import api, models

class HrEmployee(models.Model):

    _inherit = 'hr.employee'

    def get_barcodes_and_pin_hashed(self):
        if not self.env.user.has_group('point_of_sale.group_pos_user'):
            return []
        # Apply visibility filters (record rules)
        visible_emp_ids = self.search([('id', 'in', self.ids)])
        employees_data = self.sudo().search_read([('id', 'in', visible_emp_ids.ids)], ['barcode', 'pin'])

        for e in employees_data:
            e['barcode'] = hashlib.sha1(e['barcode'].encode('utf8')).hexdigest() if e['barcode'] else False
            e['pin'] = hashlib.sha1(e['pin'].encode('utf8')).hexdigest() if e['pin'] else False
        return employees_data
