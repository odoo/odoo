from odoo import api, fields, models


class Test_Search_PanelSource_Model(models.Model):
    _name = 'test_search_panel.source_model'
    _description = 'Source Model'

    name = fields.Char('Name', required=True)
    state = fields.Selection([('a', "A"), ('b', "B")])
    folder_id = fields.Many2one('test_search_panel.category_target_model')
    categ_id = fields.Many2one(
        'test_search_panel.category_target_model_no_parent_name')
    tag_ids = fields.Many2many(
        'test_search_panel.filter_target_model', 'rel_table', string="Tags")
    tag_id = fields.Many2one('test_search_panel.filter_target_model', string="Tag")


class Test_Search_PanelCategory_Target_Model(models.Model):
    _name = 'test_search_panel.category_target_model'
    _order = 'name'
    _description = 'Category target model'
    _parent_name = 'parent_name_id'

    name = fields.Char('Name', required=True)
    parent_name_id = fields.Many2one('test_search_panel.category_target_model')


class Test_Search_PanelCategory_Target_Model_No_Parent_Name(models.Model):
    _name = 'test_search_panel.category_target_model_no_parent_name'
    _order = 'id desc'
    _description = 'Category target model'

    name = fields.Char('Name', required=True)


class Test_Search_PanelFilter_Target_Model(models.Model):
    _name = 'test_search_panel.filter_target_model'
    _order = 'name'
    _description = 'Filter target model'

    name = fields.Char('Name', required=True)
    status = fields.Selection(
        [('cool', "Cool"), ('unknown', 'Unknown')])
    color = fields.Char()
    folder_id = fields.Many2one('test_search_panel.category_target_model')


class TestWebMixed(models.Model):
    _name = 'test_web.mixed'
    _description = 'Test Web Mixed'

    foo = fields.Char()
    text = fields.Text()
    truth = fields.Boolean()
    count = fields.Integer()
    number = fields.Float(digits=(10, 2), default=3.14)
    number2 = fields.Float(digits='Web Precision')
    date = fields.Date()
    moment = fields.Datetime()
    now = fields.Datetime(compute='_compute_now')
    lang = fields.Selection(string='Language', selection='_get_lang')
    reference = fields.Reference(string='Related Document',
        selection='_reference_models')
    comment0 = fields.Html()
    comment1 = fields.Html(sanitize=False)
    comment2 = fields.Html(sanitize_attributes=True, strip_classes=False)
    comment3 = fields.Html(sanitize_attributes=True, strip_classes=True)
    comment4 = fields.Html(sanitize_attributes=True, strip_style=True)
    comment5 = fields.Html(sanitize_overridable=True, sanitize_attributes=False)

    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.ref('base.EUR'))
    amount = fields.Monetary()

    def _compute_now(self):
        # this is a non-stored computed field without dependencies
        for message in self:
            message.now = fields.Datetime.now()

    @api.model
    def _get_lang(self):
        return self.env['res.lang'].get_installed()

    @api.model
    def _reference_models(self):
        models = self.env['ir.model'].sudo().search([('state', '!=', 'manual')])
        return [(model.model, model.name)
                for model in models
                if not model.model.startswith('ir.')]


class TestWebBinary_Svg(models.Model):
    _name = 'test_web.binary_svg'
    _description = 'Test SVG upload'

    name = fields.Char(required=True)
    image_attachment = fields.Binary(attachment=True)
    image_wo_attachment = fields.Binary(attachment=False)
    image_wo_attachment_related = fields.Binary(
        "image wo attachment", related="image_wo_attachment",
        store=True, attachment=False,
    )
