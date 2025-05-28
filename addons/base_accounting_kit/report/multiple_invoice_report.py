# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2024-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Cybrosys Techno Solutions(<https://www.cybrosys.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
from odoo import api, models


class ReportInvoiceMultiple(models.AbstractModel):
    _name = 'report.base_accounting_kit.report_multiple_invoice'
    _inherit = 'report.account.report_invoice'
    _description = 'Report Invoice Multiple'

    @api.model
    def _get_report_values(self, docids, data=None):
        rslt = super()._get_report_values(docids, data)

        inv = rslt['docs']
        layout = inv.journal_id.company_id.external_report_layout_id.key

        if layout == 'web.external_layout_boxed':
            new_layout = 'base_accounting_kit.boxed'

        elif layout == 'web.external_layout_bold':
            new_layout = 'base_accounting_kit.bold'

        elif layout == 'web.external_layout_striped':
            new_layout = 'base_accounting_kit.striped'

        else:
            new_layout = 'base_accounting_kit.standard'

        rslt['mi_type'] = inv.journal_id.multiple_invoice_type
        rslt['mi_ids'] = inv.journal_id.multiple_invoice_ids
        rslt['txt_position'] = inv.journal_id.text_position
        rslt['body_txt_position'] = inv.journal_id.body_text_position
        rslt['txt_align'] = inv.journal_id.text_align
        rslt['layout'] = new_layout
        rslt['report_type'] = data.get('report_type') if data else ''
        return rslt
