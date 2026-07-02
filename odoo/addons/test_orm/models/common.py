from random import randint

from odoo import api, fields, models


class TestOrmMixed(models.Model):
    _name = 'test_orm.mixed'
    _description = 'Test ORM Mixed'

    # Binary Fields
    binary_with_attachment = fields.Binary()
    binary_without_attachment = fields.Binary(attachment=False)
    image_with_attachment = fields.Image()
    image_without_attachment = fields.Image(attachment=False)

    # Misc Fields
    boolean = fields.Boolean()
    json = fields.Json()

    # Numeric Fields
    integer = fields.Integer()
    float = fields.Float()
    numeric = fields.Float(digits=(0, False))
    number = fields.Float(digits=(0, 2))
    float_default = fields.Float(default=3.14)
    float_precision = fields.Float(digits='ORM Precision')
    monetary = fields.Monetary()

    # Reference Fields
    reference = fields.Reference(selection='_get_reference_selection')
    many2one_reference = fields.Many2oneReference(model_field='res_model')

    # Relational Fields
    many2one_id = fields.Many2one('test_orm.mixed_relations')
    one2many_ids = fields.One2many('test_orm.mixed_relations', 'many2one_id')
    many2many_ids = fields.Many2many('test_orm.mixed_relations')

    # Selection Fields
    selection = fields.Selection(selection=[('option_1', 'Option 1')])
    selection_str = fields.Selection(selection='_get_selection')

    # Temporal Fields
    date = fields.Date()
    moment = fields.Datetime()

    # Textual Fields
    char = fields.Char()
    html = fields.Html()
    html_dirty = fields.Html(sanitize=False)
    html_strip_classes = fields.Html(strip_classes=True)
    html_strip_style = fields.Html(strip_style=True)
    html_sanitize_override = fields.Html(sanitize_attributes=False, sanitize_overridable=True)
    text = fields.Text()

    # Other
    currency_id = fields.Many2one('res.currency')  # Needed for the monetary field.
    res_model = fields.Char()  # Needed for the many2one_reference field.

    @api.model
    def _get_selection(self):
        return [('option_1', 'Option 1')]

    @api.model
    def _get_reference_selection(self):
        models = self.env['ir.model'].sudo().search([('state', '!=', 'manual')])
        return [(model.model, model.name)
                for model in models
                if not model.model.startswith('ir.')]


class TestOrmMixedRelations(models.Model):
    # This model is used to set up 'test_orm.mixed' relations.
    _name = 'test_orm.mixed_relations'
    _description = 'Test ORM Mixed Relations'

    many2one_id = fields.Many2one('test_orm.mixed')
    one2many_ids = fields.One2many('test_orm.mixed', 'many2one_id')
    many2many_ids = fields.Many2many('test_orm.mixed')


class TestOrmMixedComputes(models.Model):
    _name = 'test_orm.mixed_computes'
    _description = 'Test ORM Mixed Computes'

    compute_without_dependency = fields.Datetime(compute='_compute_without_dependency')

    def _compute_without_dependency(self):
        for record in self:
            record.compute_without_dependency = fields.Datetime.now()


class TestOrmPartnerCategory(models.Model):
    _name = 'test_orm.partner.category'
    _description = 'Test ORM Partner Category'
    _parent_store = True

    def _get_default_color(self):
        return randint(1, 11)

    name = fields.Char(required=True, translate=True)
    active = fields.Boolean(default=True)
    color = fields.Integer(default=_get_default_color)
    parent_path = fields.Char(index=True)
    parent_id = fields.Many2one('test_orm.partner.category')
    child_ids = fields.One2many('test_orm.partner.category', 'parent_id')
    partner_ids = fields.Many2many('test_orm.partner', column1='category_id', column2='partner_id')


class TestOrmPartner(models.Model):
    _name = 'test_orm.partner'
    _description = 'Test ORM Partner'

    def _default_category(self):
        return self.env['test_orm.partner.category'].browse(self.env.context.get('category_id'))

    name = fields.Char(required=True)
    email = fields.Char()
    active = fields.Boolean(default=True)
    website = fields.Char()
    vat = fields.Char(compute='_compute_vat')
    category_id = fields.Many2many('test_orm.partner.category', column1='partner_id', column2='category_id', default=_default_category)
    user_ids = fields.One2many('test_orm.users', 'partner_id', string="user_ids")
    parent_id = fields.Many2one('test_orm.partner')
    child_ids = fields.One2many('test_orm.partner', 'parent_id')
    country_id = fields.Many2one('test_orm.country')
    state_id = fields.Many2one('test_orm.country.state')

    @api.depends('email')
    @api.depends_context('show_email')
    def _compute_display_name(self):
        # This is needed for test_onchange on test_web.
        for partner in self:
            name = partner.name

            if partner.env.context.get('show_email') and partner.email:
                name = f"{name} <{partner.email}>"

            partner.display_name = name

    def _compute_vat(self):
        self.vat = 'Tax ID'


class TestOrmUsers(models.Model):
    _name = 'test_orm.users'
    _description = 'Test ORM Users'

    name = fields.Char(required=True)
    partner_id = fields.Many2one('test_orm.partner')


class TestOrmCountry(models.Model):
    _name = 'test_orm.country'
    _description = 'Test ORM Country'
    _order = 'name, id'

    name = fields.Char(required=True)
    code = fields.Char()
    phone_code = fields.Integer()
    state_ids = fields.One2many('test_orm.country.state', 'country_id')


class TestOrmCountryState(models.Model):
    _name = 'test_orm.country.state'
    _description = 'Test ORM  Country State'

    name = fields.Char(required=True)
    code = fields.Char()
    country_id = fields.Many2one('test_orm.country')
