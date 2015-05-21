# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp.tests import common


class test_multi_company(common.TransactionCase):

    QTY = 5.0
    PRICE = 75

    def prepare(self):
        # super(test_multi_company, self).setUp()

        self.company_obj = self.registry('res.company')
        self.analytic_account_obj = self.registry('account.analytic.account')
        self.analytic_line_obj = self.registry('account.analytic.line')
        self.invoice_obj = self.registry('account.invoice')
        self.product_obj = self.registry('product.product')

        # load main company
        self.company_a = self.browse_ref('base.main_company')
        # create an analytic account
        self.aa_id = self.analytic_account_obj.create(self.cr, self.uid, {
                'name': 'Project',
                'company_id': self.company_a.id,
                'partner_id': self.ref('base.res_partner_2'),
                'pricelist_id': self.ref('product.list0'),
            })
        # set a known price on product
        self.product_obj.write(self.cr, self.uid, self.ref('product.product_product_consultant'), {
                'list_price': self.PRICE,
            })

    def create_invoice(self):
        # create an analytic line to invoice
        line_id = self.analytic_line_obj.create(self.cr, self.uid, {
                'account_id': self.aa_id,
                'amount': -1.0,
                'general_account_id': self.ref('account.a_expense'),
                'journal_id': self.ref('hr_timesheet.analytic_journal'),
                'name': 'some work',
                'product_id': self.ref('product.product_product_consultant'),
                'product_uom_id': self.ref('product.product_uom_hour'),
                'to_invoice': self.ref('hr_timesheet_invoice.timesheet_invoice_factor2'),  # 50%
                'unit_amount': self.QTY,
            })
        # XXX too strong coupling with UI?
        wizard_obj = self.registry('hr.timesheet.invoice.create')
        wizard_id = wizard_obj.create(self.cr, self.uid, {
                'date': True,
                'name': True,
                'price': True,
                'time': True,
            }, context={'active_ids': [line_id]})
        act_win = wizard_obj.do_create(self.cr, self.uid, [wizard_id], context={'active_ids': [line_id]})
        invoice_ids = self.invoice_obj.search(self.cr, self.uid, act_win['domain'])
        invoices = self.invoice_obj.browse(self.cr, self.uid, invoice_ids)
        self.assertEquals(1, len(invoices))
        return invoices[0]

    def test_00(self):
        """ invoice task work basic test """
        self.prepare()
        invoice = self.create_invoice()
        self.assertEquals(round(self.QTY * self.PRICE * 0.5, 2), invoice.amount_untaxed)

    def test_01(self):
        """ invoice task work for analytic account of other company """
        self.prepare()
        # create a company B with its own account chart
        self.company_b_id = self.company_obj.create(self.cr, self.uid, {'name': 'Company B'})
        self.company_b = self.company_obj.browse(self.cr, self.uid, self.company_b_id)
        mc_wizard = self.registry('wizard.multi.charts.accounts')
        mc_wizard_id = mc_wizard.create(self.cr, self.uid, {
                'company_id': self.company_b_id,
                'chart_template_id': self.ref('account.conf_chart0'),
                'code_digits': 2,
                'sale_tax': self.ref('account.itaxs'),
                'purchase_tax': self.ref('account.otaxs'),
                # 'complete_tax_set': config.complete_tax_set,
                'currency_id': self.company_b.currency_id.id,
            })
        mc_wizard.execute(self.cr, self.uid, [mc_wizard_id])
        # set our analytic account on company B
        self.analytic_account_obj.write(self.cr, self.uid, [self.aa_id], {
                'company_id': self.company_b_id,
            })
        invoice = self.create_invoice()
        self.assertEquals(self.company_b_id, invoice.company_id.id, "invoice created for wrong company")
        self.assertEquals(self.company_b_id, invoice.journal_id.company_id.id, "invoice created with journal of wrong company")
        self.assertEquals(self.company_b_id, invoice.invoice_line[0].account_id.company_id.id, "invoice line created with account of wrong company")
        self.assertEquals(self.company_b_id, invoice.account_id.company_id.id, "invoice line created with partner account of wrong company")
        # self.assertEquals(self.company_b_id, invoice.fiscal_position.company_id.id, "invoice line created with fiscal position of wrong company")

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
