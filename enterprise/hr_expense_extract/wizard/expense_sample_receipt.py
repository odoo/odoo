# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import datetime

from odoo import models, _, Command
from odoo.tools.misc import file_open


class ExpenseSampleReceipt(models.Model):
    _name = 'expense.sample.receipt'
    _description = 'Try Sample Receipts'

    def _action_create_expense(self, values, sample_number):
        fallback_employee = self.env['hr.employee'].search([], limit=1) or self.env['hr.employee'].create({
            'name': _('Sample Employee'),
            'company_id': self.env.company.id,
        })

        expense_categ = self.env.ref('product.cat_expense', raise_if_not_found=False)
        product = self.env.ref('hr_expense.product_product_no_cost', raise_if_not_found=False) or \
                  self.env['product.product']._load_records([
                      dict(xml_id='hr_expense.product_product_no_cost',
                           values={
                                'name': 'Expenses',
                                'list_price': 0.0,
                                'standard_price': 1.0,
                                'type': 'service',
                                'categ_id': expense_categ.id if expense_categ else self.env.ref('product.product_category_all').id,
                                'can_be_expensed': True
                           }, noupdate=True)
                  ])

        # 3/ Compute the line values
        expense_line_values = {
            'name': _("Sample Receipt: %s", values['name']),
            'product_id': product.id,
            'total_amount_currency': values['amount'],
            'date': values['date'],
            'tax_ids': [Command.clear()],
            'sample': True,
            'employee_id': self.env.user.employee_id.id or fallback_employee.id,
        }

        # 4/ Ensure we have a journal
        if not self.env['hr.expense.sheet']._default_journal_id():
            self.env['account.journal'].create({
                'type': 'purchase',
                'company_id': self.env.company.id,
                'name': 'Sample Journal',
                'code': 'SAMPLE_P',
            })

        # 5/ Create the expense
        expense = self.env['hr.expense'].create(expense_line_values)

        # 6/ Link the attachment
        image_path = 'hr_expense_extract/static/img/receipt_sample.webp'
        image = base64.b64encode(file_open(image_path, 'rb').read())
        self.env['ir.attachment'].create({
            'name': 'sample_receipt.jpeg',
            'res_id': expense.id,
            'res_model': 'hr.expense',
            'datas': image,
            'type': 'binary',
        })

        return {
            'name': expense.name,
            'type': 'ir.actions.act_window',
            'res_model': 'hr.expense',
            'view_mode': 'form',
            'views': [[False, 'form']],
            'res_id': expense.id,
        }

    def action_choose_sample(self):
        return self._action_create_expense({
            'name': 'External training',
            'amount': 1995.6,
            'date': datetime.date(2024, 5, 24)  # Same date used in the receipt animation
        }, 1)
