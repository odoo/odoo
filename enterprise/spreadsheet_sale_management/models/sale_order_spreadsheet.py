# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.osv import expression


SALE_ORDER_LINE_FIELDS = [
    'product_id',
    'product_uom_qty',
    'qty_delivered',
    'qty_invoiced',
    'qty_to_invoice',
    'product_uom',
    'price_unit',
    'price_tax',
    'price_subtotal',
]


class SpreadsheetSaleOrder(models.Model):
    _name = 'sale.order.spreadsheet'
    _inherit = 'spreadsheet.mixin'
    _description = 'Quotation Spreadsheet'

    name = fields.Char(required=True, default=lambda self: self.env._('Untitled spreadsheet'))
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    order_id = fields.Many2one('sale.order')

    def get_formview_action(self, access_uid=None):
        return self.action_open_spreadsheet()

    @api.model_create_multi
    def create(self, vals_list):
        spreadsheets = super().create(vals_list)
        for spreadsheet, vals in zip(spreadsheets, vals_list):
            if not spreadsheet.order_id and not ('spreadsheet_binary_data' in vals or 'spreadsheet_data' in vals):
                spreadsheet._dispatch_insert_list_revision()
        return spreadsheets

    def action_open_spreadsheet(self):
        return {
            'type': 'ir.actions.client',
            'tag': 'action_sale_order_spreadsheet',
            'params': {
                'spreadsheet_id': self.id,
            },
        }

    def join_spreadsheet_session(self, access_token=None):
        data = super().join_spreadsheet_session(access_token)
        data["order_id"] = self.order_id.id
        data["order_display_name"] = self.order_id.display_name
        return data

    def _empty_spreadsheet_data(self):
        data = super()._empty_spreadsheet_data()
        data['lists'] = {
            '1': {
                'columns': SALE_ORDER_LINE_FIELDS,
                'domain': [('display_type', '=', False)],
                'model': 'sale.order.line',
                'context': {},
                'orderBy': [],
                'id': '1',
                'name': _("Sale order lines"),
                'fieldMatching': {
                    'order_filter_id': {
                        'chain': 'order_id',
                        'type': 'many2one'
                    }
                }
            }
        }
        data['globalFilters'] = [
            {
                'id': 'order_filter_id',
                'type': 'relation',
                'label': _("Quote"),
                'modelName': 'sale.order',
            }
        ]
        return data

    def _dispatch_insert_list_revision(self):
        command = {
            'sheetId': 'sheet1',
            'col': 0,
            'row': 0,
            'id': '1',
            'linesNumber': 100,
            'columns': [
                {
                    'name': field_name,
                    'type': self.env['sale.order.line']._fields[field_name].type
                } for field_name in SALE_ORDER_LINE_FIELDS
            ],
            'type': 'RE_INSERT_ODOO_LIST',
        }
        table_command = {
            'type': 'CREATE_TABLE',
            'sheetId': 'sheet1',
            'tableType': 'static',
            'ranges': [{
                '_sheetId': 'sheet1',
                '_zone': {
                    'top': 0,
                    'bottom': 100,
                    'left': 0,
                    'right': len(SALE_ORDER_LINE_FIELDS) - 1,
                },
            }],
            'config': {
                'firstColumn': False,
                'hasFilters': False,
                'totalRow': False,
                'lastColumn': False,
                'numberOfHeaders': 1,
                'bandedRows': True,
                'bandedColumns': False,
                'styleId': 'TableStyleMedium5',
            }
        }
        self._dispatch_commands([command, table_command])

    @api.model
    def get_spreadsheets(self, domain=(), offset=0, limit=None):
        domain = expression.AND([domain, [("order_id", "=", False)]])
        return super().get_spreadsheets(domain, offset, limit)

    @api.model
    def _get_spreadsheet_selector(self):
        return {
            'model': self._name,
            'display_name': _("Quotation templates"),
            'sequence': 20,
            'allow_create': False,
        }

    def _check_access(self, operation):
        return super()._check_access(operation) or self.order_id._check_access(operation)
