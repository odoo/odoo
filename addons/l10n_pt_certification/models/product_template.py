from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.fields import Domain
from odoo.tools import SQL


def _l10n_pt_format_display_name(env, name, code):
    """Format a product name like core's display names: with its internal reference when shown."""
    if env.context.get('display_default_code', True) and code:
        if env.context.get('formatted_display_name'):
            return f'{name}\t--{code}--'
        return f'[{code}] {name}'
    return name


def _l10n_pt_read_pt_names(records, values_list):
    """Give the read `values_list` of `records` their name on Portuguese documents as `name`, where they have one."""
    read_records = records.browse([values['id'] for values in values_list])
    pt_names = {record.id: record.l10n_pt_product_name for record in read_records}
    for values in values_list:
        if pt_names.get(values['id']):
            values['name'] = pt_names[values['id']]


def _l10n_pt_search_pt_name(domain, operator, value):
    """`domain`, a search of products by name, also matching their name on Portuguese documents."""
    pt_domain = Domain('l10n_pt_product_name', operator, value)
    if operator in Domain.NEGATIVE_OPERATORS:
        return Domain(domain) & pt_domain
    return Domain(domain) | pt_domain


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # Despacho 8632/2014 3.3.5: the description of a product with issued documents cannot change. It is
    # taken from the name, in one language, when a Portuguese document with the product is first posted
    # or issued; Portuguese companies, their documents and the SAF-T (PT) name the product by it from
    # then on, so a company outside Portugal can still rename the product.
    l10n_pt_product_name = fields.Char(
        string="Name on Portuguese documents",
        readonly=True,
        copy=False,
        help="The name of the product when it was first used on a Portuguese document. Portuguese "
             "companies, their documents and the SAF-T (PT) keep using it, and Portuguese companies cannot "
             "rename the product.",
    )
    l10n_pt_name_locked = fields.Boolean(
        string="Name locked for Portugal",
        compute='_compute_l10n_pt_name_locked',
        help="The active company is Portuguese and the product was used on Portuguese documents: its name cannot change.",
    )

    @api.depends('l10n_pt_product_name')
    @api.depends_context('company')
    def _compute_l10n_pt_name_locked(self):
        is_pt_company = self.env.company.account_fiscal_country_id.code == 'PT'
        for template in self:
            template.l10n_pt_name_locked = is_pt_company and bool(template.l10n_pt_product_name)

    @api.model
    def _l10n_pt_shows_pt_name(self):
        """
        Whether products are named by their name on Portuguese documents: as the context key
        `l10n_pt_frozen_product_name` says when set -- documents set it from their own company, the PoS
        from its till's -- else when the active company is Portuguese.
        """
        shows_pt_name = self.env.context.get('l10n_pt_frozen_product_name')
        if shows_pt_name is None:
            return self.env.company.account_fiscal_country_id.code == 'PT'
        return bool(shows_pt_name)

    @api.depends('l10n_pt_product_name')
    @api.depends_context('company', 'l10n_pt_frozen_product_name')
    def _compute_display_name(self):
        # EXTENDS product
        super()._compute_display_name()
        if self._l10n_pt_shows_pt_name():
            for template in self.filtered('l10n_pt_product_name'):
                template.display_name = _l10n_pt_format_display_name(
                    self.env, template.l10n_pt_product_name, template.default_code,
                )

    @api.model
    def _search_display_name(self, operator, value):
        # EXTENDS product
        domain = super()._search_display_name(operator, value)
        if self._l10n_pt_shows_pt_name():
            return _l10n_pt_search_pt_name(domain, operator, value)
        return domain

    def read(self, fields=None, load='_classic_read'):
        # EXTENDS base
        # A Portuguese company sees a product by its name on Portuguese documents in every view and in
        # the PoS, which all read `name` through `read()`.
        values_list = super().read(fields, load)
        if (not fields or 'name' in fields) and self._l10n_pt_shows_pt_name():
            _l10n_pt_read_pt_names(self, values_list)
        return values_list

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if len(vals.get('name') or '') < 2:
                raise UserError(self.env._("Product names have to be at least 2 characters long."))
        return super().create(vals_list)

    def write(self, vals):
        if 'l10n_pt_product_name' in vals:
            raise UserError(self.env._("The name on Portuguese documents cannot be set by hand."))
        if 'name' in vals:
            if len(vals['name'] or '') < 2:
                raise UserError(self.env._("Product names have to be at least 2 characters long."))
            self.filtered(lambda template: template.name != vals['name'])._l10n_pt_check_rename()
        return super().write(vals)

    def _update_field_translations(self, field_name, translations, digest=None, source_lang=''):
        # EXTENDS base
        # The translation dialog saves without `write()`; the same rule holds there.
        if field_name == 'name':
            self.filtered(lambda template: any(
                template.with_context(lang=lang).name != value for lang, value in translations.items()
            ))._l10n_pt_check_rename()
        return super()._update_field_translations(field_name, translations, digest=digest, source_lang=source_lang)

    def _l10n_pt_check_rename(self):
        """A Portuguese company cannot rename a product used on Portuguese documents (Despacho 8632/2014 3.3.5)."""
        if used := self.filtered('l10n_pt_name_locked'):
            raise UserError(self.env._(
                "You cannot modify the name of a product that has been used on Portuguese documents: %(products)s.",
                products=used.mapped('display_name'),
            ))

    def _l10n_pt_freeze_name(self, langs=()):
        """
        Give the products of `self` without one their name on Portuguese documents: their name in
        Portuguese, else in the first of the language codes `langs` it is stored in, else in English.
        """
        if not (templates := self.filtered(lambda template: not template.l10n_pt_product_name)):
            return
        templates.flush_recordset(['name'])
        # Only the stored translations count: the ORM would read a missing one as the English name.
        stored_names = SQL(", ").join(
            SQL("NULLIF(name->>%s, '')", lang) for lang in dict.fromkeys(['pt_PT', *filter(None, langs), 'en_US'])
        )
        self.env.cr.execute(SQL(
            "UPDATE product_template SET l10n_pt_product_name = COALESCE(%s) WHERE id = ANY(%s) AND l10n_pt_product_name IS NULL",
            stored_names, templates.ids,
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
