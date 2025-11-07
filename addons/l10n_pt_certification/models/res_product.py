from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools import SQL


def _l10n_pt_format_display_name(env, name, code):
    """Format a product name like core's display names: with its internal reference when shown."""
    if env.context.get('display_default_code', True) and code:
        if env.context.get('formatted_display_name'):
            return f'{name}\t--{code}--'
        return f'[{code}] {name}'
    return name


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # Despacho 8632/2014 3.3.5: the description of a product with issued documents cannot change. It is
    # taken from the name, in every language, when a Portuguese document with the product is first posted
    # or issued; Portuguese documents and the SAF-T (PT) read it from then on, so a company outside
    # Portugal can still rename the product.
    l10n_pt_product_name = fields.Char(
        string="Name on Portuguese documents",
        translate=True,
        readonly=True,
        copy=False,
        help="The name of the product when it was first used on a Portuguese document. Portuguese "
             "documents and the SAF-T (PT) keep using it, and Portuguese companies cannot rename the product.",
    )

    @api.depends('l10n_pt_product_name')
    @api.depends_context('l10n_pt_frozen_product_name')
    def _compute_display_name(self):
        # EXTENDS product
        super()._compute_display_name()
        if self.env.context.get('l10n_pt_frozen_product_name'):
            for template in self.filtered('l10n_pt_product_name'):
                template.display_name = _l10n_pt_format_display_name(
                    self.env, template.l10n_pt_product_name, template.default_code,
                )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if len(vals.get('name', 0)) < 2:
                raise UserError(self.env._("Product names have to be at least 2 characters long."))
        return super().create(vals_list)

    def write(self, vals):
        if 'l10n_pt_product_name' in vals:
            raise UserError(self.env._("The name on Portuguese documents cannot be set by hand."))
        if vals.get('name'):
            if len(vals['name']) < 2:
                raise UserError(self.env._("Product names have to be at least 2 characters long."))
            self.filtered(lambda template: template.name != vals['name'])._l10n_pt_check_rename()
        return super().write(vals)

    def _update_field_translations(self, field_name, translations, digest=None, source_lang=''):
        # EXTENDS base
        # The translation dialog saves without `write()`; the same rules hold there.
        if field_name == 'l10n_pt_product_name':
            raise UserError(self.env._("The name on Portuguese documents cannot be set by hand."))
        if field_name == 'name':
            self.filtered(lambda template: any(
                template.with_context(lang=lang).name != value for lang, value in translations.items()
            ))._l10n_pt_check_rename()
        return super()._update_field_translations(field_name, translations, digest=digest, source_lang=source_lang)

    def _l10n_pt_check_rename(self):
        """A Portuguese company cannot rename a product used on Portuguese documents (Despacho 8632/2014 3.3.5)."""
        if self.env.company.account_fiscal_country_id.code == 'PT' and (used := self.filtered('l10n_pt_product_name')):
            raise UserError(self.env._(
                "You cannot modify the name of a product that has been used on Portuguese documents: %(products)s.",
                products=used.mapped('display_name'),
            ))

    def _l10n_pt_freeze_name(self):
        """Give the products of `self` without one their name on Portuguese documents: their name, in every language."""
        if not (templates := self.filtered(lambda template: not template.l10n_pt_product_name)):
            return
        templates.flush_recordset(['name'])
        # One statement copies the name in every language as it is stored.
        self.env.cr.execute(SQL(
            "UPDATE product_template SET l10n_pt_product_name = name WHERE id = ANY(%s) AND l10n_pt_product_name IS NULL",
            templates.ids,
        ))
        templates.invalidate_recordset(['l10n_pt_product_name'])
        templates.modified(['l10n_pt_product_name'])

    @api.model
    def _l10n_pt_saft_lang(self):
        """The language of the product descriptions in the SAF-T (PT): Portuguese when installed, whoever exports."""
        return 'pt_PT' if self.env['res.lang']._get_data(code='pt_PT') else 'en_US'

    @api.model
    def _l10n_pt_saft_name_sql(self, alias):
        """SQL of the SAF-T (PT) product description of the `alias` product.template row."""
        model = self.with_context(lang=self._l10n_pt_saft_lang())
        return SQL(
            "COALESCE(%s, %s)",
            model._field_to_sql(alias, 'l10n_pt_product_name'),
            model._field_to_sql(alias, 'name'),
        )

    def _l10n_pt_saft_name(self):
        """The SAF-T (PT) product description: the name on Portuguese documents, else the name."""
        self.ensure_one()
        template = self.with_context(lang=self._l10n_pt_saft_lang())
        return template.l10n_pt_product_name or template.name


class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.model_create_multi
    def create(self, values):
        res = super().create(values)
        for product in res:
            # Products should have a unique default code for Portugal.
            if 'PT' in product.fiscal_country_codes and not product.default_code:
                product.default_code = f"{product.name.replace(' ', '_').upper()[:4]}_{product.id}"
        return res

    @api.depends('product_tmpl_id.l10n_pt_product_name')
    @api.depends_context('l10n_pt_frozen_product_name')
    def _compute_display_name(self):
        # EXTENDS product
        # With `l10n_pt_frozen_product_name` in the context, Portuguese documents name a product by its
        # name on Portuguese documents.
        super()._compute_display_name()
        if self.env.context.get('l10n_pt_frozen_product_name'):
            for product in self.sudo().filtered(lambda product: product.product_tmpl_id.l10n_pt_product_name):
                pt_name = product.product_tmpl_id.l10n_pt_product_name
                variant = product.product_template_attribute_value_ids._get_combination_name()
                product.display_name = _l10n_pt_format_display_name(
                    self.env, f"{pt_name} ({variant})" if variant else pt_name, product.default_code,
                )
