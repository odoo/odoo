from markupsafe import escape

from odoo import _, api, fields, models


class PosPriceInclusionWizard(models.TransientModel):
    _name = 'pos.price.inclusion.wizard'
    _description = 'Point of Sale Price Inclusion Wizard'

    config_id = fields.Many2one('pos.config', required=True, readonly=True)
    example_text = fields.Html(compute='_compute_example_text', readonly=True)

    @api.depends('config_id')
    def _compute_example_text(self):
        for wizard in self:
            company = wizard.config_id.company_id
            currency = company.currency_id
            tax = company.account_sale_tax_id

            base_price = 10.0
            price_incl = currency.format(base_price)

            if not tax:
                factor = 1.21
                computed_price_excl = currency.round(base_price / factor)
                price_excl = currency.format(computed_price_excl)
                price_recalc = currency.format(computed_price_excl * factor)
                incl_formula = _("(%(price_incl)s) ÷ %(factor)s = %(price_excl)s excl.",
                    price_incl=price_incl, factor=factor, price_excl=price_excl)
                excl_formula = _("(%(price_excl)s) × %(factor)s = %(price_recalc)s incl.",
                    price_excl=price_excl, factor=factor, price_recalc=price_recalc)
                tax_name = "21%"
                amount_type_label = _("Percentage")
            else:
                res_incl = tax.with_context(force_price_include=True).compute_all(base_price, currency)
                price_excl_val = res_incl['total_excluded']
                res_excl = tax.with_context(force_price_include=False).compute_all(price_excl_val, currency)
                price_excl = currency.format(price_excl_val)
                price_recalc = currency.format(res_excl['total_included'])

                if tax.amount_type == 'percent':
                    factor = f"{1 + tax.amount / 100:g}"
                    incl_formula = _("(%(price_incl)s) ÷ %(factor)s = %(price_excl)s excl.",
                        price_incl=price_incl, factor=factor, price_excl=price_excl)
                    excl_formula = _("(%(price_excl)s) × %(factor)s = %(price_recalc)s incl.",
                        price_excl=price_excl, factor=factor, price_recalc=price_recalc)
                elif tax.amount_type == 'division':
                    factor = f"{1 / (1 - tax.amount / 100):g}" if tax.amount != 100 else '∞'
                    incl_formula = _("(%(price_incl)s) ÷ %(factor)s = %(price_excl)s excl.",
                        price_incl=price_incl, factor=factor, price_excl=price_excl)
                    excl_formula = _("(%(price_excl)s) × %(factor)s = %(price_recalc)s incl.",
                        price_excl=price_excl, factor=factor, price_recalc=price_recalc)
                elif tax.amount_type == 'fixed':
                    amount = currency.format(tax.amount)
                    incl_formula = _("(%(price_incl)s) − %(amount)s = %(price_excl)s excl.",
                        price_incl=price_incl, amount=amount, price_excl=price_excl)
                    excl_formula = _("(%(price_excl)s) + %(amount)s = %(price_recalc)s incl.",
                        price_excl=price_excl, amount=amount, price_recalc=price_recalc)
                else:
                    incl_formula = _("Computed tax amount: %(price_incl)s → %(price_excl)s excl.",
                        price_incl=price_incl, price_excl=price_excl)
                    excl_formula = _("Computed tax amount: %(price_excl)s → %(price_recalc)s incl.",
                        price_excl=price_excl, price_recalc=price_recalc)

                amount_type_label = dict(tax._fields['amount_type']._description_selection(wizard.env)).get(tax.amount_type, tax.amount_type)
                tax_name = escape(tax.name)

            wizard.example_text = f"""
                <div class="d-flex flex-column gap-1">
                    <div>{_('You want to sell a product at %(price_incl)s using tax "%(tax_name)s" (%(amount_type_label)s)',
                        price_incl=price_incl, tax_name=tax_name, amount_type_label=amount_type_label)}</div>
                    <div class="d-grid" style="grid-template-columns: max-content 1fr">
                        <span class="me-1">{_('Tax included:')}</span>
                        <span>{incl_formula}</span>
                        <span class="me-1">{_('Tax excluded:')}</span>
                        <span>{excl_formula}</span>
                    </div>
                </div>
            """

    def action_tax_included(self):
        self.ensure_one()
        self.config_id.company_id.sudo().account_price_include = 'tax_included'
        return self.config_id.open_ui()

    def action_tax_excluded(self):
        self.ensure_one()
        self.config_id.company_id.sudo().account_price_include = 'tax_excluded'
        return self.config_id.open_ui()

    def action_discard(self):
        return {"type": "ir.actions.act_window_close"}
