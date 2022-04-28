# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import datetime, time
from dateutil.relativedelta import relativedelta

from markupsafe import escape, Markup
from pytz import timezone, UTC
from werkzeug.urls import url_encode

from odoo import api, fields, models, _
from odoo.osv import expression
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, format_amount, format_date, formatLang, get_lang, groupby
from odoo.tools.float_utils import float_compare, float_is_zero, float_round
from odoo.exceptions import UserError, ValidationError


class PurchaseOrder(models.Model):
    _name = "purchase.order"
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']
    _description = "Purchase Order"
    _rec_names_search = ['name', 'partner_ref']
    _order = 'priority desc, id desc'

    @api.depends('order_line.price_total')
    def _amount_all(self):
        for order in self:
            order_lines = order.order_line.filtered(lambda x: not x.display_type)
            order.amount_untaxed = sum(order_lines.mapped('price_subtotal'))
            order.amount_total = sum(order_lines.mapped('price_total'))
            order.amount_tax = sum(order_lines.mapped('price_tax'))

    @api.depends('state', 'order_line.qty_to_invoice')
    def _get_invoiced(self):
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        for order in self:
            if order.state not in ('purchase', 'done'):
                order.invoice_status = 'no'
                continue

            if any(
                not float_is_zero(line.qty_to_invoice, precision_digits=precision)
                for line in order.order_line.filtered(lambda l: not l.display_type)
            ):
                order.invoice_status = 'to invoice'
            elif (
                all(
                    float_is_zero(line.qty_to_invoice, precision_digits=precision)
                    for line in order.order_line.filtered(lambda l: not l.display_type)
                )
                and order.invoice_ids
            ):
                order.invoice_status = 'invoiced'
            else:
                order.invoice_status = 'no'

    @api.depends('order_line.invoice_lines.move_id')
    def _compute_invoice(self):
        for order in self:
            invoices = order.mapped('order_line.invoice_lines.move_id')
            order.invoice_ids = invoices
            order.invoice_count = len(invoices)

    READONLY_STATES = {
        'purchase': [('readonly', True)],
        'done': [('readonly', True)],
        'cancel': [('readonly', True)],
    }

    name = fields.Char('Order Reference', required=True, index='trigram', copy=False, default='New')
    priority = fields.Selection(
        [('0', 'Normal'), ('1', 'Urgent')], 'Priority', default='0', index=True)
    origin = fields.Char('Source Document', copy=False,
        help="Reference of the document that generated this purchase order "
             "request (e.g. a sales order)")
    partner_ref = fields.Char('Vendor Reference', copy=False,
        help="Reference of the sales order or bid sent by the vendor. "
             "It's used to do the matching when you receive the "
             "products as this reference is usually written on the "
             "delivery order sent by your vendor.")
    date_order = fields.Datetime('Order Deadline', required=True, states=READONLY_STATES, index=True, copy=False, default=fields.Datetime.now,
        help="Depicts the date within which the Quotation should be confirmed and converted into a purchase order.")
    date_approve = fields.Datetime('Confirmation Date', readonly=1, index=True, copy=False)
    partner_id = fields.Many2one('res.partner', string='Vendor', required=True, states=READONLY_STATES, change_default=True, tracking=True, domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]", help="You can find a vendor by its Name, TIN, Email or Internal Reference.")
    dest_address_id = fields.Many2one('res.partner', domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]", string='Dropship Address', states=READONLY_STATES,
        help="Put an address if you want to deliver directly from the vendor to the customer. "
             "Otherwise, keep empty to deliver to your own company.")
    currency_id = fields.Many2one('res.currency', 'Currency', required=True, states=READONLY_STATES,
        default=lambda self: self.env.company.currency_id.id)
    state = fields.Selection([
        ('draft', 'RFQ'),
        ('sent', 'RFQ Sent'),
        ('to approve', 'To Approve'),
        ('purchase', 'Purchase Order'),
        ('done', 'Locked'),
        ('cancel', 'Cancelled')
    ], string='Status', readonly=True, index=True, copy=False, default='draft', tracking=True)
    order_line = fields.One2many('purchase.order.line', 'order_id', string='Order Lines', states={'cancel': [('readonly', True)], 'done': [('readonly', True)]}, copy=True)
    notes = fields.Html('Terms and Conditions')

    invoice_count = fields.Integer(compute="_compute_invoice", string='Bill Count', copy=False, default=0, store=True)
    invoice_ids = fields.Many2many('account.move', compute="_compute_invoice", string='Bills', copy=False, store=True)
    invoice_status = fields.Selection([
        ('no', 'Nothing to Bill'),
        ('to invoice', 'Waiting Bills'),
        ('invoiced', 'Fully Billed'),
    ], string='Billing Status', compute='_get_invoiced', store=True, readonly=True, copy=False, default='no')
    date_planned = fields.Datetime(
        string='Expected Arrival', index=True, copy=False, compute='_compute_date_planned', store=True, readonly=False,
        help="Delivery date promised by vendor. This date is used to determine expected arrival of products.")
    date_calendar_start = fields.Datetime(compute='_compute_date_calendar_start', readonly=True, store=True)

    amount_untaxed = fields.Monetary(string='Untaxed Amount', store=True, readonly=True, compute='_amount_all', tracking=True)
    tax_totals = fields.Binary(compute='_compute_tax_totals')
    amount_tax = fields.Monetary(string='Taxes', store=True, readonly=True, compute='_amount_all')
    amount_total = fields.Monetary(string='Total', store=True, readonly=True, compute='_amount_all')

    fiscal_position_id = fields.Many2one('account.fiscal.position', string='Fiscal Position', domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    tax_country_id = fields.Many2one(
        comodel_name='res.country',
        compute='_compute_tax_country_id',
        # Avoid access error on fiscal position, when reading a purchase order with company != user.company_ids
        compute_sudo=True,
        help="Technical field to filter the available taxes depending on the fiscal country and fiscal position.")
    payment_term_id = fields.Many2one('account.payment.term', 'Payment Terms', domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    incoterm_id = fields.Many2one('account.incoterms', 'Incoterm', states={'done': [('readonly', True)]}, help="International Commercial Terms are a series of predefined commercial terms used in international transactions.")

    product_id = fields.Many2one('product.product', related='order_line.product_id', string='Product')
    user_id = fields.Many2one(
        'res.users', string='Buyer', index=True, tracking=True,
        default=lambda self: self.env.user, check_company=True)
    company_id = fields.Many2one('res.company', 'Company', required=True, index=True, states=READONLY_STATES, default=lambda self: self.env.company.id)
    country_code = fields.Char(related='company_id.account_fiscal_country_id.code', string="Country code")
    currency_rate = fields.Float("Currency Rate", compute='_compute_currency_rate', compute_sudo=True, store=True, readonly=True, help='Ratio between the purchase order currency and the company currency')

    mail_reminder_confirmed = fields.Boolean("Reminder Confirmed", default=False, readonly=True, copy=False, help="True if the reminder email is confirmed by the vendor.")
    mail_reception_confirmed = fields.Boolean("Reception Confirmed", default=False, readonly=True, copy=False, help="True if PO reception is confirmed by the vendor.")

    receipt_reminder_email = fields.Boolean('Receipt Reminder Email', related='partner_id.receipt_reminder_email', readonly=False)
    reminder_date_before_receipt = fields.Integer('Days Before Receipt', related='partner_id.reminder_date_before_receipt', readonly=False)

    @api.constrains('company_id', 'order_line')
    def _check_order_line_company_id(self):
        for order in self:
            companies = order.order_line.product_id.company_id
            if companies and companies != order.company_id:
                bad_products = order.order_line.product_id.filtered(lambda p: p.company_id and p.company_id != order.company_id)
                raise ValidationError(_(
                    "Your quotation contains products from company %(product_company)s whereas your quotation belongs to company %(quote_company)s. \n Please change the company of your quotation or remove the products from other companies (%(bad_products)s).",
                    product_company=', '.join(companies.mapped('display_name')),
                    quote_company=order.company_id.display_name,
                    bad_products=', '.join(bad_products.mapped('display_name')),
                ))

    def _compute_access_url(self):
        super(PurchaseOrder, self)._compute_access_url()
        for order in self:
            order.access_url = '/my/purchase/%s' % (order.id)

    @api.depends('state', 'date_order', 'date_approve')
    def _compute_date_calendar_start(self):
        for order in self:
            order.date_calendar_start = order.date_approve if (order.state in ['purchase', 'done']) else order.date_order

    @api.depends('date_order', 'currency_id', 'company_id', 'company_id.currency_id')
    def _compute_currency_rate(self):
        for order in self:
            order.currency_rate = self.env['res.currency']._get_conversion_rate(order.company_id.currency_id, order.currency_id, order.company_id, order.date_order)

    @api.depends('order_line.date_planned')
    def _compute_date_planned(self):
        """ date_planned = the earliest date_planned across all order lines. """
        for order in self:
            dates_list = order.order_line.filtered(lambda x: not x.display_type and x.date_planned).mapped('date_planned')
            if dates_list:
                order.date_planned = min(dates_list)
            else:
                order.date_planned = False

    @api.depends('name', 'partner_ref')
    def name_get(self):
        result = []
        for po in self:
            name = po.name
            if po.partner_ref:
                name += ' (' + po.partner_ref + ')'
            if self.env.context.get('show_total_amount') and po.amount_total:
                name += ': ' + formatLang(self.env, po.amount_total, currency_obj=po.currency_id)
            result.append((po.id, name))
        return result

    @api.depends('order_line.taxes_id', 'order_line.price_subtotal', 'amount_total', 'amount_untaxed')
    def  _compute_tax_totals(self):
        for order in self:
            order_lines = order.order_line.filtered(lambda x: not x.display_type)
            order.tax_totals = self.env['account.tax']._prepare_tax_totals(
                [x._convert_to_tax_base_line_dict() for x in order_lines],
                order.currency_id,
            )

    @api.depends('company_id.account_fiscal_country_id', 'fiscal_position_id.country_id', 'fiscal_position_id.foreign_vat')
    def _compute_tax_country_id(self):
        for record in self:
            if record.fiscal_position_id.foreign_vat:
                record.tax_country_id = record.fiscal_position_id.country_id
            else:
                record.tax_country_id = record.company_id.account_fiscal_country_id

    @api.onchange('date_planned')
    def onchange_date_planned(self):
        if self.date_planned:
            self.order_line.filtered(lambda line: not line.display_type).date_planned = self.date_planned

    def write(self, vals):
        vals, partner_vals = self._write_partner_values(vals)
        res = super().write(vals)
        if partner_vals:
            self.partner_id.sudo().write(partner_vals)  # Because the purchase user doesn't have write on `res.partner`
        return res

    @api.model_create_multi
    def create(self, vals_list):
        orders = self.browse()
        partner_vals_list = []
        for vals in vals_list:
            company_id = vals.get('company_id', self.default_get(['company_id'])['company_id'])
            # Ensures default picking type and currency are taken from the right company.
            self_comp = self.with_company(company_id)
            if vals.get('name', 'New') == 'New':
                seq_date = None
                if 'date_order' in vals:
                    seq_date = fields.Datetime.context_timestamp(self, fields.Datetime.to_datetime(vals['date_order']))
                vals['name'] = self_comp.env['ir.sequence'].next_by_code('purchase.order', sequence_date=seq_date) or '/'
            vals, partner_vals = self._write_partner_values(vals)
            partner_vals_list.append(partner_vals)
            orders |= super(PurchaseOrder, self_comp).create(vals)
        for order, partner_vals in zip(orders, partner_vals_list):
            if partner_vals:
                order.sudo().write(partner_vals)  # Because the purchase user doesn't have write on `res.partner`
        return orders

    @api.ondelete(at_uninstall=False)
    def _unlink_if_cancelled(self):
        for order in self:
            if not order.state == 'cancel':
                raise UserError(_('In order to delete a purchase order, you must cancel it first.'))

    def copy(self, default=None):
        ctx = dict(self.env.context)
        ctx.pop('default_product_id', None)
        self = self.with_context(ctx)
        new_po = super(PurchaseOrder, self).copy(default=default)
        for line in new_po.order_line:
            if line.product_id:
                seller = line.product_id._select_seller(
                    partner_id=line.partner_id, quantity=line.product_qty,
                    date=line.order_id.date_order and line.order_id.date_order.date(), uom_id=line.product_uom)
                line.date_planned = line._get_date_planned(seller)
        return new_po

    def _must_delete_date_planned(self, field_name):
        # To be overridden
        return field_name == 'order_line'

    def onchange(self, values, field_name, field_onchange):
        """Override onchange to NOT to update all date_planned on PO lines when
        date_planned on PO is updated by the change of date_planned on PO lines.
        """
        result = super(PurchaseOrder, self).onchange(values, field_name, field_onchange)
        if self._must_delete_date_planned(field_name) and 'value' in result:
            already_exist = [ol[1] for ol in values.get('order_line', []) if ol[1]]
            for line in result['value'].get('order_line', []):
                if line[0] < 2 and 'date_planned' in line[2] and line[1] in already_exist:
                    del line[2]['date_planned']
        return result

    def _get_report_base_filename(self):
        self.ensure_one()
        return 'Purchase Order-%s' % (self.name)

    @api.onchange('partner_id', 'company_id')
    def onchange_partner_id(self):
        # Ensures all properties and fiscal positions
        # are taken with the company of the order
        # if not defined, with_company doesn't change anything.
        self = self.with_company(self.company_id)
        if not self.partner_id:
            self.fiscal_position_id = False
            self.currency_id = self.env.company.currency_id.id
        else:
            self.fiscal_position_id = self.env['account.fiscal.position']._get_fiscal_position(self.partner_id)
            self.payment_term_id = self.partner_id.property_supplier_payment_term_id.id
            self.currency_id = self.partner_id.property_purchase_currency_id.id or self.env.company.currency_id.id
        return {}

    @api.onchange('fiscal_position_id', 'company_id')
    def _compute_tax_id(self):
        """
        Trigger the recompute of the taxes if the fiscal position is changed on the PO.
        """
        self.order_line._compute_tax_id()

    @api.onchange('partner_id')
    def onchange_partner_id_warning(self):
        if not self.partner_id or not self.env.user.has_group('purchase.group_warning_purchase'):
            return

        partner = self.partner_id

        # If partner has no warning, check its company
        if partner.purchase_warn == 'no-message' and partner.parent_id:
            partner = partner.parent_id

        if partner.purchase_warn and partner.purchase_warn != 'no-message':
            # Block if partner only has warning but parent company is blocked
            if partner.purchase_warn != 'block' and partner.parent_id and partner.parent_id.purchase_warn == 'block':
                partner = partner.parent_id
            title = _("Warning for %s", partner.name)
            message = partner.purchase_warn_msg
            warning = {
                'title': title,
                'message': message
            }
            if partner.purchase_warn == 'block':
                self.update({'partner_id': False})
            return {'warning': warning}
        return {}

    # ------------------------------------------------------------
    # MAIL.THREAD
    # ------------------------------------------------------------

    @api.returns('mail.message', lambda value: value.id)
    def message_post(self, **kwargs):
        if self.env.context.get('mark_rfq_as_sent'):
            self.filtered(lambda o: o.state == 'draft').write({'state': 'sent'})
        return super(PurchaseOrder, self.with_context(mail_post_autofollow=self.env.context.get('mail_post_autofollow', True))).message_post(**kwargs)

    def _notify_get_recipients_groups(self, msg_vals=None):
        """ Tweak 'view document' button for portal customers, calling directly
        routes for confirm specific to PO model. """
        groups = super(PurchaseOrder, self)._notify_get_recipients_groups(msg_vals=msg_vals)
        if not self:
            return groups

        self.ensure_one()
        customer_portal_group = next(group for group in groups if group[0] == 'portal_customer')
        if customer_portal_group:
            access_opt = customer_portal_group[2].setdefault('button_access', {})
            if self.env.context.get('is_reminder'):
                access_opt['title'] = _('View')
                actions = customer_portal_group[2].setdefault('actions', list())
                actions.extend([
                    {'url': self.get_confirm_url(confirm_type='reminder'), 'title': _('Accept')},
                    {'url': self.get_update_url(), 'title': _('Update Dates')},
                ])
            else:
                access_opt['title'] = _('Confirm')
                access_opt['url'] = self.get_confirm_url(confirm_type='reception')

        return groups

    def _notify_by_email_prepare_rendering_context(self, message, msg_vals, model_description=False,
                                                   force_email_company=False, force_email_lang=False):
        render_context = super()._notify_by_email_prepare_rendering_context(
            message, msg_vals, model_description=model_description,
            force_email_company=force_email_company, force_email_lang=force_email_lang
        )
        subtitles = [render_context['record'].name]
        # don't show price on RFQ mail
        if self.state not in ['draft', 'sent']:
            if self.date_order:
                subtitles.append(_('%(amount)s due\N{NO-BREAK SPACE}%(date)s',
                                   amount=format_amount(self.env, self.amount_total, self.currency_id, lang_code=render_context.get('lang')),
                                   date=format_date(self.env, self.date_order, date_format='short', lang_code=render_context.get('lang'))
                                   ))
            else:
                subtitles.append(format_amount(self.env, self.amount_total, self.currency_id, lang_code=render_context.get('lang')))
        render_context['subtitles'] = subtitles
        return render_context

    def _track_subtype(self, init_values):
        self.ensure_one()
        if 'state' in init_values and self.state == 'purchase':
            if init_values['state'] == 'to approve':
                return self.env.ref('purchase.mt_rfq_approved')
            return self.env.ref('purchase.mt_rfq_confirmed')
        elif 'state' in init_values and self.state == 'to approve':
            return self.env.ref('purchase.mt_rfq_confirmed')
        elif 'state' in init_values and self.state == 'done':
            return self.env.ref('purchase.mt_rfq_done')
        elif 'state' in init_values and self.state == 'sent':
            return self.env.ref('purchase.mt_rfq_sent')
        return super(PurchaseOrder, self)._track_subtype(init_values)

    # ------------------------------------------------------------
    # ACTIONS
    # ------------------------------------------------------------

    def action_rfq_send(self):
        '''
        This function opens a window to compose an email, with the edi purchase template message loaded by default
        '''
        self.ensure_one()
        ir_model_data = self.env['ir.model.data']
        try:
            if self.env.context.get('send_rfq', False):
                template_id = ir_model_data._xmlid_lookup('purchase.email_template_edi_purchase')[2]
            else:
                template_id = ir_model_data._xmlid_lookup('purchase.email_template_edi_purchase_done')[2]
        except ValueError:
            template_id = False
        try:
            compose_form_id = ir_model_data._xmlid_lookup('mail.email_compose_message_wizard_form')[2]
        except ValueError:
            compose_form_id = False
        ctx = dict(self.env.context or {})
        ctx.update({
            'default_model': 'purchase.order',
            'active_model': 'purchase.order',
            'active_id': self.ids[0],
            'default_res_id': self.ids[0],
            'default_use_template': bool(template_id),
            'default_template_id': template_id,
            'default_composition_mode': 'comment',
            'default_email_layout_xmlid': "mail.mail_notification_layout_with_responsible_signature",
            'force_email': True,
            'mark_rfq_as_sent': True,
        })

        # In the case of a RFQ or a PO, we want the "View..." button in line with the state of the
        # object. Therefore, we pass the model description in the context, in the language in which
        # the template is rendered.
        lang = self.env.context.get('lang')
        if {'default_template_id', 'default_model', 'default_res_id'} <= ctx.keys():
            template = self.env['mail.template'].browse(ctx['default_template_id'])
            if template and template.lang:
                lang = template._render_lang([ctx['default_res_id']])[ctx['default_res_id']]

        self = self.with_context(lang=lang)
        if self.state in ['draft', 'sent']:
            ctx['model_description'] = _('Request for Quotation')
        else:
            ctx['model_description'] = _('Purchase Order')

        return {
            'name': _('Compose Email'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form_id, 'form')],
            'view_id': compose_form_id,
            'target': 'new',
            'context': ctx,
        }

    def print_quotation(self):
        self.write({'state': "sent"})
        return self.env.ref('purchase.report_purchase_quotation').report_action(self)

    def button_approve(self, force=False):
        self = self.filtered(lambda order: order._approval_allowed())
        self.write({'state': 'purchase', 'date_approve': fields.Datetime.now()})
        self.filtered(lambda p: p.company_id.po_lock == 'lock').write({'state': 'done'})
        return {}

    def button_draft(self):
        self.write({'state': 'draft'})
        return {}

    def button_confirm(self):
        for order in self:
            if order.state not in ['draft', 'sent']:
                continue
            order._add_supplier_to_product()
            # Deal with double validation process
            if order._approval_allowed():
                order.button_approve()
            else:
                order.write({'state': 'to approve'})
            if order.partner_id not in order.message_partner_ids:
                order.message_subscribe([order.partner_id.id])
        return True

    def button_cancel(self):
        for order in self:
            for inv in order.invoice_ids:
                if inv and inv.state not in ('cancel', 'draft'):
                    raise UserError(_("Unable to cancel this purchase order. You must first cancel the related vendor bills."))

        self.write({'state': 'cancel', 'mail_reminder_confirmed': False})

    def button_unlock(self):
        self.write({'state': 'purchase'})

    def button_done(self):
        self.write({'state': 'done', 'priority': '0'})

    def _prepare_supplier_info(self, partner, line, price, currency):
        # Prepare supplierinfo data when adding a product
        return {
            'partner_id': partner.id,
            'sequence': max(line.product_id.seller_ids.mapped('sequence')) + 1 if line.product_id.seller_ids else 1,
            'min_qty': 1.0,
            'price': price,
            'currency_id': currency.id,
            'delay': 0,
        }

    def _add_supplier_to_product(self):
        # Add the partner in the supplier list of the product if the supplier is not registered for
        # this product. We limit to 10 the number of suppliers for a product to avoid the mess that
        # could be caused for some generic products ("Miscellaneous").
        for line in self.order_line:
            # Do not add a contact as a supplier
            partner = self.partner_id if not self.partner_id.parent_id else self.partner_id.parent_id
            if line.product_id and partner not in line.product_id.seller_ids.partner_id and len(line.product_id.seller_ids) <= 10:
                # Convert the price in the right currency.
                currency = partner.property_purchase_currency_id or self.env.company.currency_id
                price = self.currency_id._convert(line.price_unit, currency, line.company_id, line.date_order or fields.Date.today(), round=False)
                # Compute the price for the template's UoM, because the supplier's UoM is related to that UoM.
                if line.product_id.product_tmpl_id.uom_po_id != line.product_uom:
                    default_uom = line.product_id.product_tmpl_id.uom_po_id
                    price = line.product_uom._compute_price(price, default_uom)

                supplierinfo = self._prepare_supplier_info(partner, line, price, currency)
                # In case the order partner is a contact address, a new supplierinfo is created on
                # the parent company. In this case, we keep the product name and code.
                seller = line.product_id._select_seller(
                    partner_id=line.partner_id,
                    quantity=line.product_qty,
                    date=line.order_id.date_order and line.order_id.date_order.date(),
                    uom_id=line.product_uom)
                if seller:
                    supplierinfo['product_name'] = seller.product_name
                    supplierinfo['product_code'] = seller.product_code
                vals = {
                    'seller_ids': [(0, 0, supplierinfo)],
                }
                # supplier info should be added regardless of the user access rights
                line.product_id.sudo().write(vals)

    def action_create_invoice(self):
        """Create the invoice associated to the PO.
        """
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')

        # 1) Prepare invoice vals and clean-up the section lines
        invoice_vals_list = []
        sequence = 10
        for order in self:
            if order.invoice_status != 'to invoice':
                continue

            order = order.with_company(order.company_id)
            pending_section = None
            # Invoice values.
            invoice_vals = order._prepare_invoice()
            # Invoice line values (keep only necessary sections).
            for line in order.order_line:
                if line.display_type == 'line_section':
                    pending_section = line
                    continue
                if not float_is_zero(line.qty_to_invoice, precision_digits=precision):
                    if pending_section:
                        line_vals = pending_section._prepare_account_move_line()
                        line_vals.update({'sequence': sequence})
                        invoice_vals['invoice_line_ids'].append((0, 0, line_vals))
                        sequence += 1
                        pending_section = None
                    line_vals = line._prepare_account_move_line()
                    line_vals.update({'sequence': sequence})
                    invoice_vals['invoice_line_ids'].append((0, 0, line_vals))
                    sequence += 1
            invoice_vals_list.append(invoice_vals)

        if not invoice_vals_list:
            raise UserError(_('There is no invoiceable line. If a product has a control policy based on received quantity, please make sure that a quantity has been received.'))

        # 2) group by (company_id, partner_id, currency_id) for batch creation
        new_invoice_vals_list = []
        for grouping_keys, invoices in groupby(invoice_vals_list, key=lambda x: (x.get('company_id'), x.get('partner_id'), x.get('currency_id'))):
            origins = set()
            payment_refs = set()
            refs = set()
            ref_invoice_vals = None
            for invoice_vals in invoices:
                if not ref_invoice_vals:
                    ref_invoice_vals = invoice_vals
                else:
                    ref_invoice_vals['invoice_line_ids'] += invoice_vals['invoice_line_ids']
                origins.add(invoice_vals['invoice_origin'])
                payment_refs.add(invoice_vals['payment_reference'])
                refs.add(invoice_vals['ref'])
            ref_invoice_vals.update({
                'ref': ', '.join(refs)[:2000],
                'invoice_origin': ', '.join(origins),
                'payment_reference': len(payment_refs) == 1 and payment_refs.pop() or False,
            })
            new_invoice_vals_list.append(ref_invoice_vals)
        invoice_vals_list = new_invoice_vals_list

        # 3) Create invoices.
        moves = self.env['account.move']
        AccountMove = self.env['account.move'].with_context(default_move_type='in_invoice')
        for vals in invoice_vals_list:
            moves |= AccountMove.with_company(vals['company_id']).create(vals)

        # 4) Some moves might actually be refunds: convert them if the total amount is negative
        # We do this after the moves have been created since we need taxes, etc. to know if the total
        # is actually negative or not
        moves.filtered(lambda m: m.currency_id.round(m.amount_total) < 0).action_switch_invoice_into_refund_credit_note()

        return self.action_view_invoice(moves)

    def _prepare_invoice(self):
        """Prepare the dict of values to create the new invoice for a purchase order.
        """
        self.ensure_one()
        move_type = self._context.get('default_move_type', 'in_invoice')

        partner_invoice = self.env['res.partner'].browse(self.partner_id.address_get(['invoice'])['invoice'])
        partner_bank_id = self.partner_id.commercial_partner_id.bank_ids.filtered_domain(['|', ('company_id', '=', False), ('company_id', '=', self.company_id.id)])[:1]

        invoice_vals = {
            'ref': self.partner_ref or '',
            'move_type': move_type,
            'narration': self.notes,
            'currency_id': self.currency_id.id,
            'invoice_user_id': self.user_id and self.user_id.id or self.env.user.id,
            'partner_id': partner_invoice.id,
            'fiscal_position_id': (self.fiscal_position_id or self.fiscal_position_id._get_fiscal_position(partner_invoice)).id,
            'payment_reference': self.partner_ref or '',
            'partner_bank_id': partner_bank_id.id,
            'invoice_origin': self.name,
            'invoice_payment_term_id': self.payment_term_id.id,
            'invoice_line_ids': [],
            'company_id': self.company_id.id,
        }
        return invoice_vals

    def action_view_invoice(self, invoices=False):
        """This function returns an action that display existing vendor bills of
        given purchase order ids. When only one found, show the vendor bill
        immediately.
        """
        if not invoices:
            # Invoice_ids may be filtered depending on the user. To ensure we get all
            # invoices related to the purchase order, we read them in sudo to fill the
            # cache.
            self.invalidate_model(['invoice_ids'])
            self.sudo()._read(['invoice_ids'])
            invoices = self.invoice_ids

        result = self.env['ir.actions.act_window']._for_xml_id('account.action_move_in_invoice_type')
        # choose the view_mode accordingly
        if len(invoices) > 1:
            result['domain'] = [('id', 'in', invoices.ids)]
        elif len(invoices) == 1:
            res = self.env.ref('account.view_move_form', False)
            form_view = [(res and res.id or False, 'form')]
            if 'views' in result:
                result['views'] = form_view + [(state, view) for state, view in result['views'] if view != 'form']
            else:
                result['views'] = form_view
            result['res_id'] = invoices.id
        else:
            result = {'type': 'ir.actions.act_window_close'}

        return result

    @api.model
    def retrieve_dashboard(self):
        """ This function returns the values to populate the custom dashboard in
            the purchase order views.
        """
        self.check_access_rights('read')

        result = {
            'all_to_send': 0,
            'all_waiting': 0,
            'all_late': 0,
            'my_to_send': 0,
            'my_waiting': 0,
            'my_late': 0,
            'all_avg_order_value': 0,
            'all_avg_days_to_purchase': 0,
            'all_total_last_7_days': 0,
            'all_sent_rfqs': 0,
            'company_currency_symbol': self.env.company.currency_id.symbol
        }

        one_week_ago = fields.Datetime.to_string(fields.Datetime.now() - relativedelta(days=7))

        query = """SELECT COUNT(1)
                   FROM mail_message m
                   JOIN purchase_order po ON (po.id = m.res_id)
                   WHERE m.create_date >= %s
                     AND m.model = 'purchase.order'
                     AND m.message_type = 'notification'
                     AND m.subtype_id = %s
                     AND po.company_id = %s;
                """

        self.env.cr.execute(query, (one_week_ago, self.env.ref('purchase.mt_rfq_sent').id, self.env.company.id))
        res = self.env.cr.fetchone()
        result['all_sent_rfqs'] = res[0] or 0

        # easy counts
        po = self.env['purchase.order']
        result['all_to_send'] = po.search_count([('state', '=', 'draft')])
        result['my_to_send'] = po.search_count([('state', '=', 'draft'), ('user_id', '=', self.env.uid)])
        result['all_waiting'] = po.search_count([('state', '=', 'sent'), ('date_order', '>=', fields.Datetime.now())])
        result['my_waiting'] = po.search_count([('state', '=', 'sent'), ('date_order', '>=', fields.Datetime.now()), ('user_id', '=', self.env.uid)])
        result['all_late'] = po.search_count([('state', 'in', ['draft', 'sent', 'to approve']), ('date_order', '<', fields.Datetime.now())])
        result['my_late'] = po.search_count([('state', 'in', ['draft', 'sent', 'to approve']), ('date_order', '<', fields.Datetime.now()), ('user_id', '=', self.env.uid)])

        # Calculated values ('avg order value', 'avg days to purchase', and 'total last 7 days') note that 'avg order value' and
        # 'total last 7 days' takes into account exchange rate and current company's currency's precision.
        # This is done via SQL for scalability reasons
        query = """SELECT AVG(COALESCE(po.amount_total / NULLIF(po.currency_rate, 0), po.amount_total)),
                          AVG(extract(epoch from age(po.date_approve,po.create_date)/(24*60*60)::decimal(16,2))),
                          SUM(CASE WHEN po.date_approve >= %s THEN COALESCE(po.amount_total / NULLIF(po.currency_rate, 0), po.amount_total) ELSE 0 END)
                   FROM purchase_order po
                   WHERE po.state in ('purchase', 'done')
                     AND po.company_id = %s
                """
        self._cr.execute(query, (one_week_ago, self.env.company.id))
        res = self.env.cr.fetchone()
        result['all_avg_days_to_purchase'] = round(res[1] or 0, 2)
        currency = self.env.company.currency_id
        result['all_avg_order_value'] = format_amount(self.env, res[0] or 0, currency)
        result['all_total_last_7_days'] = format_amount(self.env, res[2] or 0, currency)

        return result

    def _send_reminder_mail(self, send_single=False):
        if not self.user_has_groups('purchase.group_send_reminder'):
            return

        template = self.env.ref('purchase.email_template_edi_purchase_reminder', raise_if_not_found=False)
        if template:
            orders = self if send_single else self._get_orders_to_remind()
            for order in orders:
                date = order.date_planned
                if date and (send_single or (date - relativedelta(days=order.reminder_date_before_receipt)).date() == datetime.today().date()):
                    if send_single:
                        return order._send_reminder_open_composer(template.id)
                    else:
                        order.with_context(is_reminder=True).message_post_with_template(template.id, email_layout_xmlid="mail.mail_notification_layout_with_responsible_signature", composition_mode='comment')

    def send_reminder_preview(self):
        self.ensure_one()
        if not self.user_has_groups('purchase.group_send_reminder'):
            return

        template = self.env.ref('purchase.email_template_edi_purchase_reminder', raise_if_not_found=False)
        if template and self.env.user.email and self.id:
            template.with_context(is_reminder=True).send_mail(
                self.id,
                force_send=True,
                raise_exception=False,
                email_layout_xmlid="mail.mail_notification_layout_with_responsible_signature",
                email_values={'email_to': self.env.user.email, 'recipient_ids': []},
            )
            return {'toast_message': escape(_("A sample email has been sent to %s.", self.env.user.email))}

    def _send_reminder_open_composer(self,template_id):
        self.ensure_one()
        try:
            compose_form_id = self.env['ir.model.data']._xmlid_lookup('mail.email_compose_message_wizard_form')[2]
        except ValueError:
            compose_form_id = False
        ctx = dict(self.env.context or {})
        ctx.update({
            'default_model': 'purchase.order',
            'active_model': 'purchase.order',
            'active_id': self.ids[0],
            'default_res_id': self.ids[0],
            'default_use_template': bool(template_id),
            'default_template_id': template_id,
            'default_composition_mode': 'comment',
            'default_email_layout_xmlid': "mail.mail_notification_layout_with_responsible_signature",
            'force_email': True,
            'mark_rfq_as_sent': True,
        })
        lang = self.env.context.get('lang')
        if {'default_template_id', 'default_model', 'default_res_id'} <= ctx.keys():
            template = self.env['mail.template'].browse(ctx['default_template_id'])
            if template and template.lang:
                lang = template._render_lang([ctx['default_res_id']])[ctx['default_res_id']]
        self = self.with_context(lang=lang)
        ctx['model_description'] = _('Purchase Order')
        return {
            'name': _('Compose Email'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form_id, 'form')],
            'view_id': compose_form_id,
            'target': 'new',
            'context': ctx,
        }

    @api.model
    def _get_orders_to_remind(self):
        """When auto sending a reminder mail, only send for unconfirmed purchase
        order and not all products are service."""
        return self.search([
            ('receipt_reminder_email', '=', True),
            ('state', 'in', ['purchase', 'done']),
            ('mail_reminder_confirmed', '=', False)
        ]).filtered(lambda p: p.mapped('order_line.product_id.product_tmpl_id.type') != ['service'])

    def get_confirm_url(self, confirm_type=None):
        """Create url for confirm reminder or purchase reception email for sending
        in mail."""
        if confirm_type in ['reminder', 'reception']:
            param = url_encode({
                'confirm': confirm_type,
                'confirmed_date': self.date_planned and self.date_planned.date(),
            })
            return self.get_portal_url(query_string='&%s' % param)
        return self.get_portal_url()

    def get_update_url(self):
        """Create portal url for user to update the scheduled date on purchase
        order lines."""
        update_param = url_encode({'update': 'True'})
        return self.get_portal_url(query_string='&%s' % update_param)

    def confirm_reminder_mail(self, confirmed_date=False):
        for order in self:
            if order.state in ['purchase', 'done'] and not order.mail_reminder_confirmed:
                order.mail_reminder_confirmed = True
                date = confirmed_date or self.date_planned.date()
                order.message_post(body=_("%s confirmed the receipt will take place on %s.", order.partner_id.name, date))

    def _approval_allowed(self):
        """Returns whether the order qualifies to be approved by the current user"""
        self.ensure_one()
        return (
            self.company_id.po_double_validation == 'one_step'
            or (self.company_id.po_double_validation == 'two_step'
                and self.amount_total < self.env.company.currency_id._convert(
                    self.company_id.po_double_validation_amount, self.currency_id, self.company_id,
                    self.date_order or fields.Date.today()))
            or self.user_has_groups('purchase.group_purchase_manager'))

    def _confirm_reception_mail(self):
        for order in self:
            if order.state in ['purchase', 'done'] and not order.mail_reception_confirmed:
                order.mail_reception_confirmed = True
                order.message_post(body=_("The order receipt has been acknowledged by %s.", order.partner_id.name))

    def _update_date_planned_for_lines(self, updated_dates):
        # create or update the activity
        activity = self.env['mail.activity'].search([
            ('summary', '=', _('Date Updated')),
            ('res_model_id', '=', 'purchase.order'),
            ('res_id', '=', self.id),
            ('user_id', '=', self.user_id.id)], limit=1)
        if activity:
            self._update_update_date_activity(updated_dates, activity)
        else:
            self._create_update_date_activity(updated_dates)

        # update the date on PO line
        for line, date in updated_dates:
            line._update_date_planned(date)

    def _create_update_date_activity(self, updated_dates):
        note = Markup('<p>%s</p>\n') % _('%s modified receipt dates for the following products:', self.partner_id.name)
        for line, date in updated_dates:
            note += Markup('<p> - %s</p>\n') % _(
                '%(product)s from %(original_receipt_date)s to %(new_receipt_date)s',
                product=line.product_id.display_name,
                original_receipt_date=line.date_planned.date(),
                new_receipt_date=date.date()
            )
        activity = self.activity_schedule(
            'mail.mail_activity_data_warning',
            summary=_("Date Updated"),
            user_id=self.user_id.id
        )
        # add the note after we post the activity because the note can be soon
        # changed when updating the date of the next PO line. So instead of
        # sending a mail with incomplete note, we send one with no note.
        activity.note = note
        return activity

    def _update_update_date_activity(self, updated_dates, activity):
        for line, date in updated_dates:
            activity.note += Markup('<p> - %s</p>\n') %  _(
                '%(product)s from %(original_receipt_date)s to %(new_receipt_date)s',
                product=line.product_id.display_name,
                original_receipt_date=line.date_planned.date(),
                new_receipt_date=date.date()
            )

    def _write_partner_values(self, vals):
        partner_values = {}
        if 'receipt_reminder_email' in vals:
            partner_values['receipt_reminder_email'] = vals.pop('receipt_reminder_email')
        if 'reminder_date_before_receipt' in vals:
            partner_values['reminder_date_before_receipt'] = vals.pop('reminder_date_before_receipt')
        return vals, partner_values


class PurchaseOrderLine(models.Model):
    _name = 'purchase.order.line'
    _inherit = 'analytic.mixin'
    _description = 'Purchase Order Line'
    _order = 'order_id, sequence, id'

    name = fields.Text(
        string='Description', required=True, compute='_compute_price_unit_and_date_planned_and_name', store=True, readonly=False)
    sequence = fields.Integer(string='Sequence', default=10)
    product_qty = fields.Float(string='Quantity', digits='Product Unit of Measure', required=True,
                               compute='_compute_product_qty', store=True, readonly=False)
    product_uom_qty = fields.Float(string='Total Quantity', compute='_compute_product_uom_qty', store=True)
    date_planned = fields.Datetime(
        string='Expected Arrival', index=True,
        compute="_compute_price_unit_and_date_planned_and_name", readonly=False, store=True,
        help="Delivery date expected from vendor. This date respectively defaults to vendor pricelist lead time then today's date.")
    taxes_id = fields.Many2many('account.tax', string='Taxes', domain=['|', ('active', '=', False), ('active', '=', True)])
    product_uom = fields.Many2one('uom.uom', string='Unit of Measure', domain="[('category_id', '=', product_uom_category_id)]")
    product_uom_category_id = fields.Many2one(related='product_id.uom_id.category_id')
    product_id = fields.Many2one('product.product', string='Product', domain=[('purchase_ok', '=', True)], change_default=True, index='btree_not_null')
    product_type = fields.Selection(related='product_id.detailed_type', readonly=True)
    price_unit = fields.Float(
        string='Unit Price', required=True, digits='Product Price',
        compute="_compute_price_unit_and_date_planned_and_name", readonly=False, store=True)

    price_subtotal = fields.Monetary(compute='_compute_amount', string='Subtotal', store=True)
    price_total = fields.Monetary(compute='_compute_amount', string='Total', store=True)
    price_tax = fields.Float(compute='_compute_amount', string='Tax', store=True)

    order_id = fields.Many2one('purchase.order', string='Order Reference', index=True, required=True, ondelete='cascade')

    company_id = fields.Many2one('res.company', related='order_id.company_id', string='Company', store=True, readonly=True)
    state = fields.Selection(related='order_id.state', store=True)

    invoice_lines = fields.One2many('account.move.line', 'purchase_line_id', string="Bill Lines", readonly=True, copy=False)

    # Replace by invoiced Qty
    qty_invoiced = fields.Float(compute='_compute_qty_invoiced', string="Billed Qty", digits='Product Unit of Measure', store=True)

    qty_received_method = fields.Selection([('manual', 'Manual')], string="Received Qty Method", compute='_compute_qty_received_method', store=True,
        help="According to product configuration, the received quantity can be automatically computed by mechanism :\n"
             "  - Manual: the quantity is set manually on the line\n"
             "  - Stock Moves: the quantity comes from confirmed pickings\n")
    qty_received = fields.Float("Received Qty", compute='_compute_qty_received', inverse='_inverse_qty_received', compute_sudo=True, store=True, digits='Product Unit of Measure')
    qty_received_manual = fields.Float("Manual Received Qty", digits='Product Unit of Measure', copy=False)
    qty_to_invoice = fields.Float(compute='_compute_qty_invoiced', string='To Invoice Quantity', store=True, readonly=True,
                                  digits='Product Unit of Measure')

    partner_id = fields.Many2one('res.partner', related='order_id.partner_id', string='Partner', readonly=True, store=True)
    currency_id = fields.Many2one(related='order_id.currency_id', store=True, string='Currency', readonly=True)
    date_order = fields.Datetime(related='order_id.date_order', string='Order Date', readonly=True)
    date_approve = fields.Datetime(related="order_id.date_approve", string='Confirmation Date', readonly=True)
    product_packaging_id = fields.Many2one('product.packaging', string='Packaging', domain="[('purchase', '=', True), ('product_id', '=', product_id)]", check_company=True,
                                           compute="_compute_product_packaging_id", store=True, readonly=False)
    product_packaging_qty = fields.Float('Packaging Quantity', compute="_compute_product_packaging_qty", store=True, readonly=False)

    display_type = fields.Selection([
        ('line_section', "Section"),
        ('line_note', "Note")], default=False, help="Technical field for UX purpose.")

    _sql_constraints = [
        ('accountable_required_fields',
            "CHECK(display_type IS NOT NULL OR (product_id IS NOT NULL AND product_uom IS NOT NULL AND date_planned IS NOT NULL))",
            "Missing required fields on accountable purchase order line."),
        ('non_accountable_null_fields',
            "CHECK(display_type IS NULL OR (product_id IS NULL AND price_unit = 0 AND product_uom_qty = 0 AND product_uom IS NULL AND date_planned is NULL))",
            "Forbidden values on non-accountable purchase order line"),
    ]

    @api.depends('product_qty', 'price_unit', 'taxes_id')
    def _compute_amount(self):
        for line in self:
            tax_results = self.env['account.tax']._compute_taxes([line._convert_to_tax_base_line_dict()])
            totals = list(tax_results['totals'].values())[0]
            amount_untaxed = totals['amount_untaxed']
            amount_tax = totals['amount_tax']

            line.update({
                'price_subtotal': amount_untaxed,
                'price_tax': amount_tax,
                'price_total': amount_untaxed + amount_tax,
            })

    def _convert_to_tax_base_line_dict(self):
        """ Convert the current record to a dictionary in order to use the generic taxes computation method
        defined on account.tax.

        :return: A python dictionary.
        """
        self.ensure_one()
        return self.env['account.tax']._convert_to_tax_base_line_dict(
            self,
            partner=self.order_id.partner_id,
            currency=self.order_id.currency_id,
            product=self.product_id,
            taxes=self.taxes_id,
            price_unit=self.price_unit,
            quantity=self.product_qty,
            price_subtotal=self.price_subtotal,
        )

    def _compute_tax_id(self):
        for line in self:
            line = line.with_company(line.company_id)
            fpos = line.order_id.fiscal_position_id or line.order_id.fiscal_position_id._get_fiscal_position(line.order_id.partner_id)
            # filter taxes by company
            taxes = line.product_id.supplier_taxes_id.filtered(lambda r: r.company_id == line.env.company)
            line.taxes_id = fpos.map_tax(taxes)

    @api.depends('invoice_lines.move_id.state', 'invoice_lines.quantity', 'qty_received', 'product_uom_qty', 'order_id.state')
    def _compute_qty_invoiced(self):
        for line in self:
            # compute qty_invoiced
            qty = 0.0
            for inv_line in line._get_invoice_lines():
                if inv_line.move_id.state not in ['cancel'] or inv_line.move_id.payment_state == 'invoicing_legacy':
                    if inv_line.move_id.move_type == 'in_invoice':
                        qty += inv_line.product_uom_id._compute_quantity(inv_line.quantity, line.product_uom)
                    elif inv_line.move_id.move_type == 'in_refund':
                        qty -= inv_line.product_uom_id._compute_quantity(inv_line.quantity, line.product_uom)
            line.qty_invoiced = qty

            # compute qty_to_invoice
            if line.order_id.state in ['purchase', 'done']:
                if line.product_id.purchase_method == 'purchase':
                    line.qty_to_invoice = line.product_qty - line.qty_invoiced
                else:
                    line.qty_to_invoice = line.qty_received - line.qty_invoiced
            else:
                line.qty_to_invoice = 0

    def _get_invoice_lines(self):
        self.ensure_one()
        if self._context.get('accrual_entry_date'):
            return self.invoice_lines.filtered(
                lambda l: l.move_id.invoice_date and l.move_id.invoice_date <= self._context['accrual_entry_date']
            )
        else:
            return self.invoice_lines

    @api.depends('product_id')
    def _compute_qty_received_method(self):
        for line in self:
            if line.product_id and line.product_id.type in ['consu', 'service']:
                line.qty_received_method = 'manual'
            else:
                line.qty_received_method = False

    @api.depends('qty_received_method', 'qty_received_manual')
    def _compute_qty_received(self):
        for line in self:
            if line.qty_received_method == 'manual':
                line.qty_received = line.qty_received_manual or 0.0
            else:
                line.qty_received = 0.0

    @api.onchange('qty_received')
    def _inverse_qty_received(self):
        """ When writing on qty_received, if the value should be modify manually (`qty_received_method` = 'manual' only),
            then we put the value in `qty_received_manual`. Otherwise, `qty_received_manual` should be False since the
            received qty is automatically compute by other mecanisms.
        """
        for line in self:
            if line.qty_received_method == 'manual':
                line.qty_received_manual = line.qty_received
            else:
                line.qty_received_manual = 0.0

    @api.model_create_multi
    def create(self, vals_list):
        for values in vals_list:
            if values.get('display_type', self.default_get(['display_type'])['display_type']):
                values.update(product_id=False, price_unit=0, product_uom_qty=0, product_uom=False, date_planned=False)
            else:
                values.update(self._prepare_add_missing_fields(values))

        lines = super().create(vals_list)
        for line in lines:
            if line.product_id and line.order_id.state == 'purchase':
                msg = _("Extra line with %s ") % (line.product_id.display_name,)
                line.order_id.message_post(body=msg)
        return lines

    def write(self, values):
        if 'display_type' in values and self.filtered(lambda line: line.display_type != values.get('display_type')):
            raise UserError(_("You cannot change the type of a purchase order line. Instead you should delete the current line and create a new line of the proper type."))

        if 'product_qty' in values:
            for line in self:
                if line.order_id.state == 'purchase':
                    line.order_id.message_post_with_view('purchase.track_po_line_template',
                                                         values={'line': line, 'product_qty': values['product_qty']},
                                                         subtype_id=self.env.ref('mail.mt_note').id)
        if 'qty_received' in values:
            for line in self:
                line._track_qty_received(values['qty_received'])
        return super(PurchaseOrderLine, self).write(values)

    @api.ondelete(at_uninstall=False)
    def _unlink_except_purchase_or_done(self):
        for line in self:
            if line.order_id.state in ['purchase', 'done']:
                state_description = {state_desc[0]: state_desc[1] for state_desc in self._fields['state']._description_selection(self.env)}
                raise UserError(_('Cannot delete a purchase order line which is in state \'%s\'.') % (state_description.get(line.state),))

    @api.model
    def _get_date_planned(self, seller, po=False):
        """Return the datetime value to use as Schedule Date (``date_planned``) for
           PO Lines that correspond to the given product.seller_ids,
           when ordered at `date_order_str`.

           :param Model seller: used to fetch the delivery delay (if no seller
                                is provided, the delay is 0)
           :param Model po: purchase.order, necessary only if the PO line is
                            not yet attached to a PO.
           :rtype: datetime
           :return: desired Schedule Date for the PO line
        """
        date_order = po.date_order if po else self.order_id.date_order
        if date_order:
            return date_order + relativedelta(days=seller.delay if seller else 0)
        else:
            return datetime.today() + relativedelta(days=seller.delay if seller else 0)

    @api.depends('product_id', 'order_id.partner_id')
    def _compute_analytic_distribution_stored_char(self):
        for line in self:
            if not line.display_type:
                distribution = self.env['account.analytic.distribution.model']._get_distributionjson({
                    "product_id": line.product_id.id,
                    "product_categ_id": line.product_id.categ_id.id,
                    "partner_id": line.order_id.partner_id.id,
                    "partner_category_id": line.order_id.partner_id.category_id.ids,
                    "company_id": line.company_id.id,
                })
                line.analytic_distribution_stored_char = distribution or line.analytic_distribution_stored_char
                line._compute_analytic_distribution()

    @api.onchange('product_id')
    def onchange_product_id(self):
        if not self.product_id:
            return

        # Reset date, price and quantity since _onchange_quantity will provide default values
        self.price_unit = self.product_qty = 0.0

        self._product_id_change()

        self._suggest_quantity()

    def _product_id_change(self):
        if not self.product_id:
            return

        self.product_uom = self.product_id.uom_po_id or self.product_id.uom_id
        product_lang = self.product_id.with_context(
            lang=get_lang(self.env, self.partner_id.lang).code,
            partner_id=self.partner_id.id,
            company_id=self.company_id.id,
        )
        self.name = self._get_product_purchase_description(product_lang)

        self._compute_tax_id()

    @api.onchange('product_id')
    def onchange_product_id_warning(self):
        if not self.product_id or not self.env.user.has_group('purchase.group_warning_purchase'):
            return
        warning = {}
        title = False
        message = False

        product_info = self.product_id

        if product_info.purchase_line_warn != 'no-message':
            title = _("Warning for %s", product_info.name)
            message = product_info.purchase_line_warn_msg
            warning['title'] = title
            warning['message'] = message
            if product_info.purchase_line_warn == 'block':
                self.product_id = False
            return {'warning': warning}
        return {}

    @api.depends('product_qty', 'product_uom')
    def _compute_price_unit_and_date_planned_and_name(self):
        for line in self:
            if not line.product_id or line.invoice_lines:
                continue
            params = {'order_id': line.order_id}
            seller = line.product_id._select_seller(
                partner_id=line.partner_id,
                quantity=line.product_qty,
                date=line.order_id.date_order and line.order_id.date_order.date(),
                uom_id=line.product_uom,
                params=params)

            if seller or not line.date_planned:
                line.date_planned = line._get_date_planned(seller).strftime(DEFAULT_SERVER_DATETIME_FORMAT)

            # If not seller, use the standard price. It needs a proper currency conversion.
            if not seller:
                po_line_uom = line.product_uom or line.product_id.uom_po_id
                price_unit = line.env['account.tax']._fix_tax_included_price_company(
                    line.product_id.uom_id._compute_price(line.product_id.standard_price, po_line_uom),
                    line.product_id.supplier_taxes_id,
                    line.taxes_id,
                    line.company_id,
                )
                line.price_unit = line.currency_id._convert(
                    price_unit,
                    line.currency_id,
                    line.company_id,
                    line.date_order,
                )
                continue

            price_unit = line.env['account.tax']._fix_tax_included_price_company(seller.price, line.product_id.supplier_taxes_id, line.taxes_id, line.company_id) if seller else 0.0
            price_unit = seller.currency_id._convert(price_unit, line.currency_id, line.company_id, line.date_order)
            line.price_unit = seller.product_uom._compute_price(price_unit, line.product_uom)

            # record product names to avoid resetting custom descriptions
            default_names = []
            vendors = line.product_id._prepare_sellers({})
            for vendor in vendors:
                product_ctx = {'seller_id': vendor.id, 'lang': get_lang(line.env, line.partner_id.lang).code}
                default_names.append(line._get_product_purchase_description(line.product_id.with_context(product_ctx)))
            if not line.name or line.name in default_names:
                product_ctx = {'seller_id': seller.id, 'lang': get_lang(line.env, line.partner_id.lang).code}
                line.name = line._get_product_purchase_description(line.product_id.with_context(product_ctx))

    @api.depends('product_id', 'product_qty', 'product_uom')
    def _compute_product_packaging_id(self):
        for line in self:
            # remove packaging if not match the product
            if line.product_packaging_id.product_id != line.product_id:
                line.product_packaging_id = False
            # suggest biggest suitable packaging
            if line.product_id and line.product_qty and line.product_uom:
                line.product_packaging_id = line.product_id.packaging_ids.filtered('purchase')._find_suitable_product_packaging(line.product_qty, line.product_uom)

    @api.onchange('product_packaging_id')
    def _onchange_product_packaging_id(self):
        if self.product_packaging_id and self.product_qty:
            newqty = self.product_packaging_id._check_qty(self.product_qty, self.product_uom, "UP")
            if float_compare(newqty, self.product_qty, precision_rounding=self.product_uom.rounding) != 0:
                return {
                    'warning': {
                        'title': _('Warning'),
                        'message': _(
                            "This product is packaged by %(pack_size).2f %(pack_name)s. You should purchase %(quantity).2f %(unit)s.",
                            pack_size=self.product_packaging_id.qty,
                            pack_name=self.product_id.uom_id.name,
                            quantity=newqty,
                            unit=self.product_uom.name
                        ),
                    },
                }

    @api.depends('product_packaging_id', 'product_uom', 'product_qty')
    def _compute_product_packaging_qty(self):
        for line in self:
            if not line.product_packaging_id:
                line.product_packaging_qty = 0
            else:
                packaging_uom = line.product_packaging_id.product_uom_id
                packaging_uom_qty = line.product_uom._compute_quantity(line.product_qty, packaging_uom)
                line.product_packaging_qty = float_round(packaging_uom_qty / line.product_packaging_id.qty, precision_rounding=packaging_uom.rounding)

    @api.depends('product_packaging_qty')
    def _compute_product_qty(self):
        for line in self:
            if line.product_packaging_id:
                packaging_uom = line.product_packaging_id.product_uom_id
                qty_per_packaging = line.product_packaging_id.qty
                product_qty = packaging_uom._compute_quantity(line.product_packaging_qty * qty_per_packaging, line.product_uom)
                if float_compare(product_qty, line.product_qty, precision_rounding=line.product_uom.rounding) != 0:
                    line.product_qty = product_qty

    @api.depends('product_uom', 'product_qty', 'product_id.uom_id')
    def _compute_product_uom_qty(self):
        for line in self:
            if line.product_id and line.product_id.uom_id != line.product_uom:
                line.product_uom_qty = line.product_uom._compute_quantity(line.product_qty, line.product_id.uom_id)
            else:
                line.product_uom_qty = line.product_qty

    def action_purchase_history(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("purchase.action_purchase_history")
        action['domain'] = [('state', 'in', ['purchase', 'done']), ('product_id', '=', self.product_id.id)]
        action['display_name'] = _("Purchase History for %s", self.product_id.display_name)
        action['context'] = {
            'search_default_partner_id': self.partner_id.id
        }

        return action

    def _suggest_quantity(self):
        '''
        Suggest a minimal quantity based on the seller
        '''
        if not self.product_id:
            return
        seller_min_qty = self.product_id.seller_ids\
            .filtered(lambda r: r.partner_id == self.order_id.partner_id and (not r.product_id or r.product_id == self.product_id))\
            .sorted(key=lambda r: r.min_qty)
        if seller_min_qty:
            self.product_qty = seller_min_qty[0].min_qty or 1.0
            self.product_uom = seller_min_qty[0].product_uom
        else:
            self.product_qty = 1.0

    def _get_product_purchase_description(self, product_lang):
        self.ensure_one()
        name = product_lang.display_name
        if product_lang.description_purchase:
            name += '\n' + product_lang.description_purchase

        return name

    def _prepare_account_move_line(self, move=False):
        self.ensure_one()
        aml_currency = move and move.currency_id or self.currency_id
        date = move and move.date or fields.Date.today()
        return {
            'display_type': self.display_type or 'product',
            'name': '%s: %s' % (self.order_id.name, self.name),
            'product_id': self.product_id.id,
            'product_uom_id': self.product_uom.id,
            'quantity': self.qty_to_invoice,
            'price_unit': self.currency_id._convert(self.price_unit, aml_currency, self.company_id, date, round=False),
            'tax_ids': [(6, 0, self.taxes_id.ids)],
            'analytic_distribution': self.analytic_distribution,
            'purchase_line_id': self.id,
        }

    @api.model
    def _prepare_add_missing_fields(self, values):
        """ Deduce missing required fields from the onchange """
        res = {}
        onchange_fields = ['name', 'price_unit', 'product_qty', 'product_uom', 'taxes_id', 'date_planned']
        if values.get('order_id') and values.get('product_id') and any(f not in values for f in onchange_fields):
            line = self.new(values)
            line.onchange_product_id()
            for field in onchange_fields:
                if field not in values:
                    res[field] = line._fields[field].convert_to_write(line[field], line)
        return res

    @api.model
    def _prepare_purchase_order_line(self, product_id, product_qty, product_uom, company_id, supplier, po):
        partner = supplier.partner_id
        uom_po_qty = product_uom._compute_quantity(product_qty, product_id.uom_po_id)
        # _select_seller is used if the supplier have different price depending
        # the quantities ordered.
        seller = product_id.with_company(company_id)._select_seller(
            partner_id=partner,
            quantity=uom_po_qty,
            date=po.date_order and po.date_order.date(),
            uom_id=product_id.uom_po_id)

        product_taxes = product_id.supplier_taxes_id.filtered(lambda x: x.company_id.id == company_id.id)
        taxes = po.fiscal_position_id.map_tax(product_taxes)

        price_unit = self.env['account.tax']._fix_tax_included_price_company(
            seller.price, product_taxes, taxes, company_id) if seller else 0.0
        if price_unit and seller and po.currency_id and seller.currency_id != po.currency_id:
            price_unit = seller.currency_id._convert(
                price_unit, po.currency_id, po.company_id, po.date_order or fields.Date.today())

        product_lang = product_id.with_prefetch().with_context(
            lang=partner.lang,
            partner_id=partner.id,
        )
        name = product_lang.with_context(seller_id=seller.id).display_name
        if product_lang.description_purchase:
            name += '\n' + product_lang.description_purchase

        date_planned = self.order_id.date_planned or self._get_date_planned(seller, po=po)

        return {
            'name': name,
            'product_qty': uom_po_qty,
            'product_id': product_id.id,
            'product_uom': product_id.uom_po_id.id,
            'price_unit': price_unit,
            'date_planned': date_planned,
            'taxes_id': [(6, 0, taxes.ids)],
            'order_id': po.id,
        }

    def _convert_to_middle_of_day(self, date):
        """Return a datetime which is the noon of the input date(time) according
        to order user's time zone, convert to UTC time.
        """
        return timezone(self.order_id.user_id.tz or self.company_id.partner_id.tz or 'UTC').localize(datetime.combine(date, time(12))).astimezone(UTC).replace(tzinfo=None)

    def _update_date_planned(self, updated_date):
        self.date_planned = updated_date

    def _track_qty_received(self, new_qty):
        self.ensure_one()
        if new_qty != self.qty_received and self.order_id.state == 'purchase':
            self.order_id.message_post_with_view(
                'purchase.track_po_line_qty_received_template',
                values={'line': self, 'qty_received': new_qty},
                subtype_id=self.env.ref('mail.mt_note').id
            )
