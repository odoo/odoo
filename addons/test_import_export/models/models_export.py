from odoo import fields, models


class ExportAggregator(models.Model):
    _name = 'export.aggregator'
    _description = 'Export Aggregator'

    int_sum = fields.Integer(aggregator='sum')
    int_max = fields.Integer(aggregator='max')
    float_min = fields.Float(aggregator='min')
    float_avg = fields.Float(aggregator='avg')
    float_monetary = fields.Monetary(currency_field='currency_id', aggregator='sum')
    currency_id = fields.Many2one('res.currency')
    date_max = fields.Date(aggregator='max')
    bool_and = fields.Boolean(aggregator='bool_and')
    bool_or = fields.Boolean(aggregator='bool_or')
    many2one = fields.Many2one('export.integer')
    one2many = fields.One2many('export.aggregator.one2many', 'parent_id')
    many2many = fields.Many2many(comodel_name='res.partner')
    active = fields.Boolean(default=True)
    parent_id = fields.Many2one('export.aggregator', string='Parent')
    definition_properties = fields.PropertiesDefinition('Definitions')
    properties = fields.Properties('Properties', definition='parent_id.definition_properties')


class ExportAggregatorOne2many(models.Model):
    _name = 'export.aggregator.one2many'
    _description = 'Export Aggregator One2Many'

    name = fields.Char()
    parent_id = fields.Many2one('export.aggregator')
    value = fields.Integer()
    active = fields.Boolean(default=True)
    admin_property_def = fields.Many2one('export.aggregator.admin')
    admin_property = fields.Properties('Properties', definition='admin_property_def.definition_properties')


class ExportAggregatorAdminOnly(models.Model):
    _name = 'export.aggregator.admin'
    _description = 'Export Aggregator only for admin'

    definition_properties = fields.PropertiesDefinition('Definitions')
