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
