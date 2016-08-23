# -*- encoding: utf-8 -*-

from datetime import date
from datetime import datetime
from decimal import Decimal

from openerp import netsvc
from openerp.osv import fields
from openerp.osv import orm

from openerp.addons.connector.unit.mapper import mapping
from openerp.addons.connector.unit.mapper import only_create

from .backend import prestashop
from .unit.backend_adapter import GenericAdapter
from .unit.mapper import PrestashopImportMapper
from .unit.import_synchronizer import PrestashopImportSynchronizer
from .connector import add_checkpoint


@prestashop
class RefundAdapter(GenericAdapter):
    _model_name = 'prestashop.refund'
    _prestashop_model = 'order_slips'


@prestashop
class RefundImport(PrestashopImportSynchronizer):
    _model_name = 'prestashop.refund'

    def _import_dependencies(self):
        record = self.prestashop_record
        self._check_dependency(record['id_customer'], 'prestashop.res.partner')
        self.session.context['so_refund_no_dep'] = True
        self._check_dependency(record['id_order'], 'prestashop.sale.order')
        del self.session.context['so_refund_no_dep']

    def _after_import(self, refund_id):
        context = self.session.context
        context['company_id'] = self.backend_record.company_id.id
        refund = self.session.browse('prestashop.refund', refund_id)
        erp_id = refund.openerp_id.id
        invoice_obj = self.session.pool.get('account.invoice')
        invoice_obj.button_reset_taxes(
            self.session.cr,
            self.session.uid,
            [erp_id],
            context=context
        )

        invoice = self.session.browse('account.invoice', erp_id)
        if invoice.amount_total == float(self.prestashop_record['amount']):
            wf_service = netsvc.LocalService("workflow")
            wf_service.trg_validate(self.session.uid, 'account.invoice',
                                    erp_id, 'invoice_open', self.session.cr)
        else:
            add_checkpoint(
                self.session,
                'account.invoice',
                erp_id,
                self.backend_record.id
            )


@prestashop
class RefundMapper(PrestashopImportMapper):
    _model_name = 'prestashop.refund'

    direct = [
        ('id', 'name'),
        ('date_add', 'date_invoice'),
    ]

    @mapping
    def journal_id(self, record):
        journal_ids = self.session.search('account.journal', [
            ('company_id', '=', self.backend_record.company_id.id),
            ('type', '=', 'sale_refund'),
        ])
        return {'journal_id': journal_ids[0]}

    def _get_order(self, record):
        binder = self.get_binder_for_model('prestashop.sale.order')
        sale_order_id = binder.to_openerp(record['id_order'])
        return self.session.browse('prestashop.sale.order', sale_order_id)

    @mapping
    def from_sale_order(self, record):
        sale_order = self._get_order(record)
        fiscal_position = None
        if sale_order.fiscal_position:
            fiscal_position = sale_order.fiscal_position.id
        return {
            'origin': sale_order['name'],
            'fiscal_position': fiscal_position,
        }

    @mapping
    def comment(self, record):
        return {'comment': 'Montant dans prestashop : %s' % (record['amount'])}

    @mapping
    @only_create
    def invoice_lines(self, record):
        slip_details = record.get('associations', {}).get('order_slip_details', []).get('order_slip_detail', [])
        if isinstance(slip_details, dict):
            slip_details = [slip_details]
        lines = []
        fpos_id = self.from_sale_order(record)['fiscal_position']
        fpos = None
        if fpos_id:
            fpos = self.session.browse('account.fiscal.position', fpos_id)
        shipping_line = self._invoice_line_shipping(record, fpos)
        if shipping_line is not None:
            lines.append((0, 0, shipping_line))
        for slip_detail in slip_details:
            line = self._invoice_line(slip_detail, fpos)
            lines.append((0, 0, line))
        return {'invoice_line': lines}

    def _invoice_line_shipping(self, record, fpos):
        order_line = self._get_shipping_order_line(record)
        if order_line is None:
            return None
        if record['shipping_cost'] == '1':
            price_unit = order_line['price_unit']
        else:
            price_unit = record['shipping_cost_amount']
        if price_unit in [0.0, '0.00']:
            return None
        product = self.session.browse(
            'product.product',
            order_line['product_id'][0]
        )
        account_id = product.property_account_income.id
        if not account_id:
            account_id = product.categ_id.property_account_income_categ.id
        if fpos:
            fpos_obj = self.session.pool['account.fiscal.position']
            account_id = fpos_obj.map_account(
                self.session.cr,
                self.session.uid,
                fpos,
                account_id
            )
        return {
            'quantity': 1,
            'product_id': product.id,
            'name': order_line['name'],
            'invoice_line_tax_id': [(6, 0, order_line['tax_id'])],
            'price_unit': price_unit,
            'discount': order_line['discount'],
            'account_id': account_id,
        }

    def _get_shipping_order_line(self, record):
        binder = self.get_binder_for_model('prestashop.sale.order')
        sale_order_id = binder.to_openerp(record['id_order'])
        sale_order = self.session.browse('prestashop.sale.order', sale_order_id)

        if not sale_order.carrier_id:
            return None

        sale_order_line_ids = self.session.search('sale.order.line', [
            ('order_id', '=', sale_order_id),
            ('product_id', '=', sale_order.carrier_id.product_id.id),
        ])
        if not sale_order_line_ids:
            return None
        return self.session.read('sale.order.line', sale_order_line_ids[0], [])

    def _invoice_line(self, record, fpos):
        order_line = self._get_order_line(record['id_order_detail'])
        tax_ids = []
        if order_line is None:
            product_id = None
            name = "Order line not found"
            account_id = None
        else:
            product = order_line.product_id
            product_id = product.id
            name = order_line.name
            for tax in order_line.tax_id:
                tax_ids.append(tax.id)
            account_id = product.property_account_income.id
            if not account_id:
                account_id = product.categ_id.property_account_income_categ.id
        if fpos and account_id:
            fpos_obj = self.session.pool['account.fiscal.position']
            account_id = fpos_obj.map_account(
                self.session.cr,
                self.session.uid,
                fpos,
                account_id
            )
        if record['product_quantity'] == '0':
            quantity = 1
        else:
            quantity = record['product_quantity']
        if self.backend_record.taxes_included:
            price_unit = record['amount_tax_incl']
        else:
            price_unit = record['amount_tax_excl']
        try:
            price_unit = float(price_unit) / float(quantity)
        except ValueError:
            pass
        discount = False
        if price_unit in ['0.00', ''] and order_line is not None:
            price_unit = order_line['price_unit']
            discount = order_line['discount']
        return {
            'quantity': quantity,
            'product_id': product_id,
            'name': name,
            'invoice_line_tax_id': [(6, 0, tax_ids)],
            'price_unit': price_unit,
            'discount': discount,
            'account_id': account_id,
        }

    def _get_order_line(self, order_details_id):
        order_line_id = self.session.search('prestashop.sale.order.line', [
            ('prestashop_id', '=', order_details_id),
            ('backend_id', '=', self.backend_record.id),
        ])
        if not order_line_id:
            return None
        context = self.session.context
        context['company_id'] = self.backend_record.company_id.id
        return self.session.pool.get('prestashop.sale.order.line').browse(
            self.session.cr,
            self.session.uid,
            order_line_id[0],
            context=context
        )

    @mapping
    def type(self, record):
        return {'type': 'out_refund'}

    @mapping
    def partner_id(self, record):
        binder = self.get_binder_for_model('prestashop.res.partner')
        partner_id = binder.to_openerp(record['id_customer'], unwrap=True)
        return {'partner_id': partner_id}

    @mapping
    def account_id(self, record):
        binder = self.get_binder_for_model('prestashop.sale.order')
        sale_order_id = binder.to_openerp(record['id_order'], unwrap=True)
        sale_order = self.session.browse('prestashop.sale.order', sale_order_id)
        date_invoice = datetime.strptime(record['date_upd'], '%Y-%m-%d %H:%M:%S')
        if date(2014, 1, 1) > date_invoice.date() and \
            sale_order.payment_method_id and sale_order.payment_method_id.account_id:
            return {'account_id': sale_order.payment_method_id.account_id.id}
        context = self.session.context
        context['company_id'] = self.backend_record.company_id.id
        binder = self.get_binder_for_model('prestashop.res.partner')
        partner_id = binder.to_openerp(record['id_customer'])
        partner = self.session.pool['prestashop.res.partner'].browse(
            self.session.cr,
            self.session.uid,
            partner_id,
            context=context
        )
        return {'account_id': partner.property_account_receivable.id}

    @mapping
    def company_id(self, record):
        return {'company_id': self.backend_record.company_id.id}

    @mapping
    def backend_id(self, record):
        return {'backend_id': self.backend_record.id}

