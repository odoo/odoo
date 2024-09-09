# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools.misc import formatLang


class L10nItDeclarationOfIntent(models.Model):
    _name = "l10n_it_edi_doi.declaration_of_intent"
    _inherit = ['mail.thread.main.attachment', 'mail.activity.mixin']
    _description = "Declaration of Intent"
    _order = 'protocol_number_part1, protocol_number_part2'

    state = fields.Selection([
         ('draft', 'Draft'),
         ('active', 'Active'),
         ('revoked', 'Revoked'),
         ('terminated', 'Terminated'),
        ],
        string="State",
        tracking=True,
        default='draft',
        required=True,
        readonly=True,
        help="The state of this Declaration of Intent. \n"
        "- 'Draft' means that the Declaration of Intent still needs to be confirmed before being usable. \n"
        "- 'Active' means that the Declaration of Intent is usable. \n"
        "- 'Terminated' designates that the Declaration of Intent has been marked as not to use anymore without invalidating usages of it. \n"
        "- 'Revoked' means the Declaration of Intent should not have been used. You will probably need to revert previous usages of it, if any.\n")

    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        index=True,
        required=True,
        default=lambda self: self.env.company._accessible_branches()[:1],
    )

    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string='Partner',
        index=True,
        required=True,
        domain="['|', ('is_company', '=', True), ('parent_id', '=', False)]",
    )

    currency_id = fields.Many2one(
        comodel_name='res.currency',
        string='Currency',
        default=lambda self: self.env.ref('base.EUR', raise_if_not_found=False).id,
        required=True,
        readonly=True,
    )

    issue_date = fields.Date(
        string='Date of Issue',
        required=True,
        copy=False,
        default=fields.Date.context_today,
        help="Date on which the Declaration of Intent was issued",
    )

    start_date = fields.Date(
        string='Start Date',
        required=True,
        copy=False,
        help="First date on which the Declaration of Intent is valid",
    )

    end_date = fields.Date(
        string='End Date',
        required=True,
        copy=False,
        help="Last date on which the Declaration of Intent is valid",
    )

    threshold = fields.Monetary(
        string='Threshold',
        required=True,
        help="Total amount of allowed sales without VAT under this Declaration of Intent",
    )

    invoiced = fields.Monetary(
        string='Invoiced',
        compute='_compute_invoiced',
        store=True,
        readonly=True,
        help="Total amount of sales under this Declaration of Intent",
    )

    not_yet_invoiced = fields.Monetary(
        string='Not Yet Invoiced',
        compute='_compute_not_yet_invoiced',
        store=True,
        readonly=True,
        help="Total amount of planned sales under this Declaration of Intent (i.e. current quotation and sales orders) that can still be invoiced",
    )

    remaining = fields.Monetary(
        string='Remaining',
        compute='_compute_remaining',
        store=True,
        readonly=True,
        help="Remaining amount after deduction of the Invoiced and Not Yet Invoiced amounts.",
    )

    protocol_number_part1 = fields.Char(
        string='Protocol 1',
        required=True,
        readonly=False,
        copy=False,
    )

    protocol_number_part2 = fields.Char(
        string='Protocol 2',
        required=True,
        readonly=False,
        copy=False,
    )

    invoice_ids = fields.One2many(
        'account.move',
        'l10n_it_edi_doi_id',
        string="Invoices / Refunds",
        copy=False,
        readonly=True,
    )

    sale_order_ids = fields.One2many(
        'sale.order',
        'l10n_it_edi_doi_id',
        string="Sales Orders / Quotations",
        copy=False,
        readonly=True,
    )

    _sql_constraints = [
        ('protocol_number_unique',
         'unique(protocol_number_part1, protocol_number_part2)',
         "The Protocol Number of a Declaration of Intent must be unique! Please choose another one."),
        ('threshold_positive',
         'CHECK(threshold > 0)',
         "The Threshold of a Declaration of Intent must be positive."),
    ]

    @api.depends('protocol_number_part1', 'protocol_number_part2')
    def _compute_display_name(self):
        for record in self:
            record.display_name = f"{record.protocol_number_part1}-{record.protocol_number_part2}"

    @api.depends('invoice_ids', 'invoice_ids.state', 'invoice_ids.l10n_it_edi_doi_amount')
    def _compute_invoiced(self):
        for declaration in self:
            relevant_invoices = declaration.invoice_ids.filtered(
                lambda invoice: invoice.state == 'posted'
            )
            declaration.invoiced = sum(relevant_invoices.mapped('l10n_it_edi_doi_amount'))

    @api.depends('sale_order_ids', 'sale_order_ids.state', 'sale_order_ids.l10n_it_edi_doi_not_yet_invoiced')
    def _compute_not_yet_invoiced(self):
        for declaration in self:
            relevant_orders = declaration.sale_order_ids.filtered(
                lambda order: order.state == 'sale'
            )
            declaration.not_yet_invoiced = sum(relevant_orders.mapped('l10n_it_edi_doi_not_yet_invoiced'))

    @api.depends('threshold', 'not_yet_invoiced', 'invoiced')
    def _compute_remaining(self):
        for record in self:
            record.remaining = record.threshold - record.invoiced - record.not_yet_invoiced

    def _build_threshold_warning_message(self, invoiced, not_yet_invoiced):
        """
        Build a warning message that will be displayed in a yellow banner on top of a document
        if the `remaining` of the Declaration of Intent is less than 0 when including the document
        or the Declaration of Intent is revoked
            :param float invoiced:          The `declaration.invoiced` amount when including the document.
            :param float not_yet_invoiced:  The `declaration.not_yet_invoiced` amount when including the document.
            :return str:                    The warning message to be shown.
        """
        self.ensure_one()
        updated_remaining = self.threshold - invoiced - not_yet_invoiced
        if self.currency_id.compare_amounts(updated_remaining, 0) >= 0:
            return ''
        return _(
            'Pay attention, the threshold of your Declaration of Intent %(name)s of %(threshold)s is exceeded by %(exceeded)s, this document included.\n'
            'Invoiced: %(invoiced)s; Not Yet Invoiced: %(not_yet_invoiced)s',
            name=self.display_name,
            threshold=formatLang(self.env, self.threshold, currency_obj=self.currency_id),
            exceeded=formatLang(self.env, - updated_remaining, currency_obj=self.currency_id),
            invoiced=formatLang(self.env, invoiced, currency_obj=self.currency_id),
            not_yet_invoiced=formatLang(self.env, not_yet_invoiced, currency_obj=self.currency_id),
        )

    def _get_validity_errors(self, company, partner, currency):
        """
        Check whether all declarations of intent in self are valid for the specified `company`, `partner`, `date` and `currency'.
        Violating these constraints leads to errors in the feature. They should not be ignored.
        Return all errors as a list of strings.
        """
        errors = []
        for declaration in self:
            if not company or declaration.company_id != company:
                errors.append(_("The Declaration of Intent belongs to company %(declaration_company)s, not %(company)s.",
                                declaration_company=declaration.company_id.name, company=company.name))
            if not currency or declaration.currency_id != currency:
                errors.append(_("The Declaration of Intent uses currency %(declaration_currency)s, not %(currency)s.",
                                declaration_currency=declaration.currency_id.name, currency=currency.name))
            if not partner or declaration.partner_id != partner.commercial_partner_id:
                errors.append(_("The Declaration of Intent belongs to partner %(declaration_partner)s, not %(partner)s.",
                                declaration_partner=declaration.partner_id.name, partner=partner.commercial_partner_id.name))
        return errors

    def _get_validity_warnings(self, company, partner, currency, date, invoiced_amount=0, only_blocking=False, sales_order=False):
        """
        Check whether all declarations of intent in self are valid for the specified `company`, `partner`, `date` and `currency'.
        The checks for `date` and state of the declaration (except draft) are not considered blocking in case `invoiced_amount` is not positive.
        All other checks are considered blocking (prevent posting).
        Includes all checks from `_get_validity_errors`.
        The checks are different for invoices and sales orders (toggled via kwarg `sales_order`).
        I.e. we do not care about the date for sales orders.
        Return all errors as a list of strings.
        """
        errors = []
        for declaration in self:
            errors.extend(declaration._get_validity_errors(company, partner, currency))
            if declaration.state == 'draft':
                errors.append(_("The Declaration of Intent is in draft."))
            if declaration.currency_id.compare_amounts(invoiced_amount, 0) > 0 or not only_blocking:
                if declaration.state != 'active':
                    errors.append(_("The Declaration of Intent must be active."))
                if not sales_order and (not date or declaration.start_date > date or declaration.end_date < date):
                    errors.append(_("The Declaration of Intent is valid from %(start_date)s to %(end_date)s, not on %(date)s.",
                                    start_date=declaration.start_date, end_date=declaration.end_date, date=date))
        return errors

    @api.model
    def _fetch_valid_declaration_of_intent(self, company, partner, currency, date):
        """
        Fetch a declaration of intent that is valid for the specified `company`, `partner`, `date` and `currency`
        and has not reached the threshold yet.
        """
        return self.search([
            ('state', '=', 'active'),
            ('company_id', '=', company.id),
            ('currency_id', '=', currency.id),
            ('partner_id', '=', partner.commercial_partner_id.id),
            ('start_date', '<=', date),
            ('end_date', '>=', date),
            ('remaining', '>', 0),
        ], limit=1)

    @api.ondelete(at_uninstall=False)
    def _unlink_except_linked_to_document(self):
        if self.invoice_ids or self.sale_order_ids:
            raise UserError(_('You cannot delete Declarations of Intents that are already used on at least one Invoice or Sales Order.'))

    def action_validate(self):
        """ Move a 'draft' Declaration of Intent to 'active'."""
        for record in self:
            if record.state == 'draft':
                record.state = 'active'

    def action_reset_to_draft(self):
        """ Resets an 'active' Declaration of Intent back to 'draft'."""
        for record in self:
            if record.state == 'active':
                record.state = 'draft'

    def action_reactivate(self):
        """ Resets a not 'active' Declaration of Intent back to 'active'."""
        for record in self:
            if record.state != 'active':
                record.state = 'active'

    def action_revoke(self):
        """ Called by the 'revoke' button of the form view."""
        for record in self:
            record.state = 'revoked'

    def action_terminate(self):
        """ Called by the 'terminated' button of the form view."""
        for record in self:
            if record.state != 'revoked':
                record.state = 'terminated'

    def action_open_sale_order_ids(self):
        self.ensure_one()
        return {
            'name': _("Sales Orders using Declaration of Intent %s", self.display_name),
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'domain': [('id', 'in', self.sale_order_ids.ids)],
            'views': [(self.env.ref('l10n_it_edi_doi.view_quotation_tree').id, 'list'), (False, 'form')],
            'search_view_id': [self.env.ref('sale.sale_order_view_search_inherit_quotation').id],
            'context': {
                'search_default_sales': 1,
            },
        }

    def action_open_invoice_ids(self):
        self.ensure_one()
        return {
            'name': _("Invoices using Declaration of Intent %s", self.display_name),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'domain': [('id', 'in', self.invoice_ids.ids)],
            'views': [(self.env.ref('l10n_it_edi_doi.view_move_tree').id, 'list'), (False, 'form')],
            'search_view_id': [self.env.ref('account.view_account_invoice_filter').id],
            'context': {
                'search_default_posted': 1,
            },
        }
