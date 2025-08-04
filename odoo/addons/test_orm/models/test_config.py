from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    test_boolean_field = fields.Boolean(
        string='Test Boolean Field',
        config_parameter='test_orm.test_boolean_field',
        help='A test boolean field for configuration settings'
    )

    test_integer_field = fields.Integer(
        string='Test Integer Field',
        config_parameter='test_orm.test_integer_field',
        help='A test integer field for configuration settings'
    )

    test_float_field = fields.Float(
        string='Test Float Field',
        digits=(10, 2),
        config_parameter='test_orm.test_float_field',
        help='A test float field for configuration settings'
    )

    test_char_field = fields.Char(
        string='Test Char Field',
        config_parameter='test_orm.test_char_field',
        help='A test char field for configuration settings'
    )

    test_selection_field = fields.Selection(
        string='Test Selection Field',
        selection=[
            ('option1', 'Option 1'),
            ('option2', 'Option 2'),
            ('option3', 'Option 3'),
        ],
        config_parameter='test_orm.test_selection_field',
        help='A test selection field for configuration settings'
    )

    test_many2one_field = fields.Many2one(
        string='Test Many2one Field',
        comodel_name='res.partner',
        config_parameter='test_orm.test_many2one_field',
        help='A test many2one field for configuration settings'
    )


    test_datetime_field = fields.Datetime(
        string='Test Datetime Field',
        config_parameter='test_orm.test_datetime_field',
        help='A test datetime field for configuration settings'
    )
