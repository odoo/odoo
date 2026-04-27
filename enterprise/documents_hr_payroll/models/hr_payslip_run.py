# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class HrPayslipRun(models.Model):
    _inherit = 'hr.payslip.run'

    def unlink(self):
        linked_documents = self.env['documents.document'].search([
            ('res_model', '=', 'hr.payslip'),
            ('res_id', 'in', self.slip_ids.ids),
            ('active', '=', True),
        ])

        for document in linked_documents:
            document.write({
                'res_model': 'documents.document',
                'res_id': document.id,
                'active': False,
            })
        return super().unlink()
