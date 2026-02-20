from odoo import _, api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    l10n_tr_nilvera_customer_alias_id = fields.Many2one(
        comodel_name='l10n_tr.nilvera.alias',
        string="eInvoice Alias",
        compute='_compute_nilvera_customer_alias_id',
        domain="[('partner_id', '=', id)]",
        copy=False,
        store=True,
        readonly=False,
        help="Specifies the alias provided by Nilvera, used when sending electronic invoices. \n"
        "It helps make sure your customer is correctly recognized by the GİB when e-invoices are sent. \n"
        "This ID is needed for your invoices to be processed correctly and comply with Turkish tax rules.",
    )
    l10n_tr_tax_office_id = fields.Many2one(
        "l10n_tr_nilvera_einvoice.tax.office",
        string="Turkish Tax Office",
        help="Specifies the official Turkish Tax Office where this partner is registered. "
             "This is required for generating valid e-Invoices for this partner.",
    )

    @api.depends('l10n_tr_tax_office_id')
    def _compute_display_name(self):
        super()._compute_display_name()
        tr_partners_with_tax_office = self.filtered("l10n_tr_tax_office_id")
        if not self.env.context.get('show_address'):
            return
        for partner in tr_partners_with_tax_office:
            if not partner.env.context.get("formatted_display_name"):
                partner.display_name = (f"{partner.display_name}\n{partner.l10n_tr_tax_office_id.name}")

    @api.depends('l10n_tr_nilvera_customer_alias_ids', 'l10n_tr_nilvera_customer_status')
    def _compute_nilvera_customer_alias_id(self):
        for record in self:
            if record.l10n_tr_nilvera_customer_status == 'einvoice' and not record.l10n_tr_nilvera_customer_alias_id:
                record.l10n_tr_nilvera_customer_alias_id = record.l10n_tr_nilvera_customer_alias_ids[:1]
            elif record.l10n_tr_nilvera_customer_status == 'earchive':
                record.l10n_tr_nilvera_customer_alias_id = False

    def _get_tax_office_missing_message(self):
        # OVERRIDE
        self.ensure_one()
        return _("The Turkish Tax Office field must be filled") if not self.l10n_tr_tax_office_id else None

    def _get_tax_office_for_edispatch(self):
        # OVERRIDE
        self.ensure_one()
        return self.l10n_tr_tax_office_id.name
