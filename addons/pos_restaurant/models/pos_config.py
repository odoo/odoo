# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class PosConfig(models.Model):
    _inherit = 'pos.config'

    iface_splitbill = fields.Boolean(string='Bill Splitting', help='Enables Bill Splitting in the Point of Sale.')
    iface_printbill = fields.Boolean(string='Bill Printing', help='Allows to print the Bill before payment.')
    iface_orderline_notes = fields.Boolean(string='Internal Notes', help='Allow custom Internal notes on Orderlines.', default=True)
    floor_ids = fields.Many2many('restaurant.floor', string='Restaurant Floors', help='The restaurant floors served by this point of sale.')
    set_tip_after_payment = fields.Boolean('Set Tip After Payment', help="Adjust the amount authorized by payment terminals to add a tip after the customers left or at the end of the day.")
    module_pos_restaurant = fields.Boolean(default=True)

    def get_tables_order_count(self):
        """         """
        self.ensure_one()
        tables = self.env['restaurant.table'].search([('floor_id.pos_config_ids', '=', self.id)])
        domain = [('state', '=', 'draft'), ('table_id', 'in', tables.ids)]

        order_stats = self.env['pos.order']._read_group(domain, ['table_id'], ['__count'])
        orders_map = {table.id: count for table, count in order_stats}

        result = []
        for table in tables:
            result.append({'id': table.id, 'orders': orders_map.get(table.id, 0)})
        return result

    def _get_forbidden_change_fields(self):
        forbidden_keys = super(PosConfig, self)._get_forbidden_change_fields()
        forbidden_keys.append('floor_ids')
        return forbidden_keys

    def write(self, vals):
        if ('module_pos_restaurant' in vals and vals['module_pos_restaurant'] is False):
            vals['floor_ids'] = [(5, 0, 0)]
        return super(PosConfig, self).write(vals)

    @api.model
    def add_cash_payment_method(self):
        companies = self.env['res.company'].search([])
        for company in companies.filtered('chart_template'):
            pos_configs = self.search([('company_id', '=', company.id), ('module_pos_restaurant', '=', True)])
            journal_counter = 2
            for pos_config in pos_configs:
                if pos_config.payment_method_ids.filtered('is_cash_count'):
                    continue
                cash_journal = self.env['account.journal'].search([('company_id', '=', company.id), ('type', '=', 'cash'), ('pos_payment_method_ids', '=', False)], limit=1)
                if not cash_journal:
                    cash_journal = self.env['account.journal'].create({
                        'name': _('Cash %s', journal_counter),
                        'code': 'RCSH%s' % journal_counter,
                        'type': 'cash',
                        'company_id': company.id
                    })
                    journal_counter += 1
                payment_methods = pos_config.payment_method_ids
                payment_methods |= self.env['pos.payment.method'].create({
                    'name': _('Cash Bar'),
                    'journal_id': cash_journal.id,
                    'company_id': company.id,
                })
                pos_config.write({'payment_method_ids': [(6, 0, payment_methods.ids)]})

    @api.model
    def post_install_pos_localisation(self, companies=False):
        self = self.sudo()
        if not companies:
            companies = self.env['res.company'].search([])
        for company in companies.filtered('chart_template'):
            pos_configs = self.search([('company_id', '=', company.id), ('module_pos_restaurant', '=', True)])
            if not pos_configs:
                self = self.with_company(company)
                pos_configs = self.env['pos.config'].create({
                'name': 'Bar',
                'company_id': company.id,
                'module_pos_restaurant': True,
                'iface_splitbill': True,
                'iface_printbill': True,
                'iface_orderline_notes': True,

            })
            pos_configs.setup_defaults(company)
            super(PosConfig, self).post_install_pos_localisation(companies)
