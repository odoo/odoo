import math
from odoo import api
from odoo.exceptions import ValidationError
from odoo import models, fields


PAPER_SIZES = [
    {
        'description': 'A0  5   841 x 1189 mm',
        'key': 'A0',
        'height': 1189.0,
        'width': 841.0,
    }, {
        'key': 'A1',
        'description': 'A1  6   594 x 841 mm',
        'height': 841.0,
        'width': 594.0,
    }, {
        'key': 'A2',
        'description': 'A2  7   420 x 594 mm',
        'height': 594.0,
        'width': 420.0,
    }, {
        'key': 'A3',
        'description': 'A3  8   297 x 420 mm',
        'height': 420.0,
        'width': 297.0,
    }, {
        'key': 'A4',
        'description': 'A4  0   210 x 297 mm, 8.26 x 11.69 inches',
        'height': 297.0,
        'width': 210.0,
    }, {
        'key': 'A5',
        'description': 'A5  9   148 x 210 mm',
        'height': 210.0,
        'width': 148.0,
    }, {
        'key': 'A6',
        'description': 'A6  10  105 x 148 mm',
        'height': 148.0,
        'width': 105.0,
    }, {
        'key': 'A7',
        'description': 'A7  11  74 x 105 mm',
        'height': 105.0,
        'width': 74.0,
    }, {
        'key': 'A8',
        'description': 'A8  12  52 x 74 mm',
        'height': 74.0,
        'width': 52.0,
    }, {
        'key': 'A9',
        'description': 'A9  13  37 x 52 mm',
        'height': 52.0,
        'width': 37.0,
    }, {
        'key': 'B0',
        'description': 'B0  14  1000 x 1414 mm',
        'height': 1414.0,
        'width': 1000.0,
    }, {
        'key': 'B1',
        'description': 'B1  15  707 x 1000 mm',
        'height': 1000.0,
        'width': 707.0,
    }, {
        'key': 'B2',
        'description': 'B2  17  500 x 707 mm',
        'height': 707.0,
        'width': 500.0,
    }, {
        'key': 'B3',
        'description': 'B3  18  353 x 500 mm',
        'height': 500.0,
        'width': 353.0,
    }, {
        'key': 'B4',
        'description': 'B4  19  250 x 353 mm',
        'height': 353.0,
        'width': 250.0,
    }, {
        'key': 'B5',
        'description': 'B5  1   176 x 250 mm, 6.93 x 9.84 inches',
        'height': 250.0,
        'width': 176.0,
    }, {
        'key': 'B6',
        'description': 'B6  20  125 x 176 mm',
        'height': 176.0,
        'width': 125.0,
    }, {
        'key': 'B7',
        'description': 'B7  21  88 x 125 mm',
        'height': 125.0,
        'width': 88.0,
    }, {
        'key': 'B8',
        'description': 'B8  22  62 x 88 mm',
        'height': 88.0,
        'width': 62.0,
    }, {
        'key': 'B9',
        'description': 'B9  23  33 x 62 mm',
        'height': 62.0,
        'width': 33.0,
    }, {
        'key': 'B10',
        'description': 'B10    16  31 x 44 mm',
        'height': 44.0,
        'width': 31.0,
    }, {
        'key': 'C5E',
        'description': 'C5E 24  163 x 229 mm',
        'height': 229.0,
        'width': 163.0,
    }, {
        'key': 'Comm10E',
        'description': 'Comm10E 25  105 x 241 mm, U.S. Common 10 Envelope',
        'height': 241.0,
        'width': 105.0,
    }, {
        'key': 'DLE',
        'description': 'DLE 26 110 x 220 mm',
        'height': 220.0,
        'width': 110.0,
    }, {
        'key': 'Executive',
        'description': 'Executive 4   7.5 x 10 inches, 190.5 x 254 mm',
        'height': 254.0,
        'width': 190.5,
    }, {
        'key': 'Folio',
        'description': 'Folio 27  210 x 330 mm',
        'height': 330.0,
        'width': 210.0,
    }, {
        'key': 'Ledger',
        'description': 'Ledger  28  431.8 x 279.4 mm',
        'height': 279.4,
        'width': 431.8,
    }, {
        'key': 'Legal',
        'description': 'Legal    3   8.5 x 14 inches, 215.9 x 355.6 mm',
        'height': 355.6,
        'width': 215.9,
    }, {
        'key': 'Letter',
        'description': 'Letter 2 8.5 x 11 inches, 215.9 x 279.4 mm',
        'height': 279.4,
        'width': 215.9,
    }, {
        'key': 'Tabloid',
        'description': 'Tabloid 29 279.4 x 431.8 mm',
        'height': 431.8,
        'width': 279.4,
    }, {
        'key': 'custom',
        'description': 'Custom',
    },
]


class check_layout_format(models.Model):
    _name = "account.check.layout.format"
    _description = "Check layout format"

    name = fields.Char(required=True)
    description = fields.Text(string='Description')

    _sql_constraints = [('check_char_seperator_length', 'CHECK (length(check_date_seperator) < 2)', 'The date seperator can be of atmost one character')]

    # Paper Format dimensions
    paper_format = fields.Selection(string='Paper Format', selection=[(ps['key'], ps['description']) for ps in PAPER_SIZES], default='A4')
    paper_width = fields.Float(compute='_compute_print_page_size')
    paper_height = fields.Float(compute='_compute_print_page_size')
    page_width = fields.Float(string='Custom Width')
    page_height = fields.Float(string='Custom Height')

    # Check Alignment and position
    check_orientation = fields.Selection(selection=[
                                            ('Portrait', 'Portrait Mode'),
                                            ('Landscape', 'Landscape Mode')],
                                               string='Orientation', default='Portrait', required=True)
    check_position = fields.Selection(string='Position', selection=[('top', 'Top'), ('bottom', 'Bottom'), ('center', 'Center'), ('custom', 'Custom')], default='center', required=True)
    check_margin_top = fields.Float(compute='_compute_check_margins')
    check_margin_left = fields.Float(compute='_compute_check_margins')
    margin_top = fields.Float(string='Custom top margin')
    margin_left = fields.Float(string='Custom left margin')

    # cross check
    is_cross_check = fields.Boolean(default=True)
    cross_check_content = fields.Char(string='Cross check content')
    cross_check_dist = fields.Float(string='Distance of cross check from top corner')
    cross_check_width = fields.Float(compute='_compute_cross_check_width')

    # Check dimensions
    check_width = fields.Float(string='Check Width', required=True)
    check_height = fields.Float(string='Check Height', required=True)

    # Check date
    check_date_dist_from_top = fields.Float(string="Margin for Date from Check's top", required=True)
    check_date_dist_from_left = fields.Float(string="Margin for Date from Check's left side", required=True)
    check_date_format = fields.Selection(selection=[('mmddyyyy', 'MMDDYYYY'),
                                                            ('yyyymmdd', 'YYYYMMDD'),
                                                            ('ddmmyyyy', 'DDMMYYYY'),
                                                            ('mmddyy', 'MMDDYY'),
                                                            ('ddmmyy', 'DDMMYY'),
                                                            ('yymmdd', 'YYMMDD')],
                                                    string='Date Format', default='ddmmyyyy', required=True)
    check_date_seperator = fields.Char(default=' ', string='Date Seperator')
    check_date_dist_bet_char = fields.Float(required=True, string='Gap between characters')

    # Payee/Party name
    payee_dist_from_top = fields.Float(string="Margin for Payee's name from Check's top", required=True)
    payee_dist_from_left = fields.Float(string="Margin for Payee's name from Check's left side", required=True)
    payee_width_area = fields.Float(string="Width Area for Payee's name", required=True)

    # amount in words
    aiw_line1_dist_from_top = fields.Float(string="Margin for Line 1 from Check's top", required=True)
    aiw_line2_dist_from_top = fields.Float(string="Margin for Line 2 from Check's top", required=True)
    aiw_line1_dist_from_left = fields.Float(string="Margin for Line 1 from Check's left side", required=True)
    aiw_line2_dist_from_left = fields.Float(string="Margin for Line 2 from Check's left side", required=True)
    aiw_line1_width_area = fields.Float(string='Width Area for Line 1', required=True)
    aiw_line2_width_area = fields.Float(string='Width Area for Line 2', required=True)
    aiw_currency_name = fields.Selection(string='Currency Name', selection=[('yes', 'Yes'), ('no', 'No')], default='yes', required=True)

    # amount in figures
    aif_dist_from_top = fields.Float(string="Margin for figure from Check's top", required=True)
    aif_dist_from_left = fields.Float(string="Margin for figure from Check's left side", required=True)
    aif_currency_symbol = fields.Selection(string='Currency Symbol', selection=[('yes', 'Yes'), ('no', 'No')], default='no', required=True)

    @api.constrains('check_width', 'check_height')
    def _check_dimensions(self):
        for record in self:
            if record.check_width > record.paper_width:
                raise ValidationError("The check width cannot be greater than the paper width")
            if record.check_height > record.paper_height:
                raise ValidationError("The check height cannot be greater than the paper height")

    @api.constrains('margin_top', 'margin_left')
    def _check_margins(self):
        for record in self:
            if record.margin_top > record.paper_height - record.check_height:
                raise ValidationError("The custom top margin must be less than the paper height")
            if record.margin_left > record.paper_width - record.check_height:
                raise ValidationError("The custom left margin must be less than the paper width")

    @api.constrains('check_date_dist_from_top', 'check_date_dist_from_left')
    def _check_date(self):
        for record in self:
            if record.check_date_dist_from_top > record.check_height:
                raise ValidationError("The distance of date from top must be less than the check height")
            if record.check_date_dist_from_left > record.check_width:
                raise ValidationError("The distance of date from left must be less than the check width")

    @api.constrains('payee_dist_from_top', 'payee_dist_from_left', 'payee_width_area')
    def _check_payee(self):
        for record in self:
            if record.payee_dist_from_top > record.check_height:
                raise ValidationError("The distance of payee name from top must be less than the check height")
            if record.payee_dist_from_left > record.check_width:
                raise ValidationError("The distance of payee name from left must be less than the check width")
            if (record.payee_width_area + record.payee_dist_from_left) > record.check_width:
                raise ValidationError("The width area must be less than the check width")

    @api.constrains('aiw_line1_dist_from_top', 'aiw_line2_dist_from_top', 'aiw_line1_dist_from_left', 'aiw_line2_dist_from_left', 'aiw_line1_width_area', 'aiw_line2_width_area')
    def _check_aiw(self):
        for record in self:
            if record.aiw_line1_dist_from_top > record.check_height:
                raise ValidationError("The distance of amount in words line 1 from top must be less than the check height")
            if record.aiw_line1_dist_from_left > record.check_width:
                raise ValidationError("The distance of amount in words line 1 from left must be less than the check width")
            if (record.aiw_line1_width_area + record.aiw_line1_dist_from_left) > record.check_width:
                raise ValidationError("The width area for amount in words line 1 must be less than the check width")
            if record.aiw_line2_dist_from_top > record.check_height:
                raise ValidationError("The distance of amount in words line 2 from top must be less than the check height")
            if record.aiw_line2_dist_from_left > record.check_width:
                raise ValidationError("The distance of pamount in words line 2 from left must be less than the check width")
            if (record.aiw_line2_width_area + record.aiw_line2_dist_from_left) > record.check_width:
                raise ValidationError("The width area for amount in words line 2 must be less than the check width")

    @api.constrains('aif_dist_from_top', 'aif_dist_from_left')
    def _check_aif(self):
        for record in self:
            if record.aif_dist_from_top > record.check_height:
                raise ValidationError("The distance of amount in figures from top must be less than the check height")
            if record.aif_dist_from_left > record.check_width:
                raise ValidationError("The distance of amount in figures from left must be less than the check width")

    def write(self, vals):
        result = super().write(vals)
        self._paper_format()
        return result

    def _paper_format(self):
        paper_format = self.env['report.paperformat'].search([('name', '=', 'Check Paper Format')], limit=1)
        if paper_format:
            paper_format.write({
                'page_height': self.paper_height if self.paper_format == 'custom' else 0.0,
                'page_width': self.paper_width if self.paper_format == 'custom' else 0.0,
                'format': self.paper_format,
                'orientation': self.check_orientation,
            })

    @api.depends('paper_format', 'page_width', 'page_height')
    def _compute_print_page_size(self):
        for record in self:
            width = height = 0.0
            if record.paper_format:
                if record.paper_format == 'custom':
                    width = record.page_width
                    height = record.page_height
                else:
                    paper_size = next(ps for ps in PAPER_SIZES if ps['key'] == record.paper_format)
                    width = paper_size['width']
                    height = paper_size['height']

            if record.check_orientation == 'Landscape':
                width, height = height, width

            record.paper_width = width
            record.paper_height = height

    @api.depends('check_width', 'check_height')
    def _compute_cross_check_width(self):
        for record in self:
            record.cross_check_width = math.pow(math.pow(record.check_width, 2) + math.pow(record.check_height, 2), 0.5)

    @api.depends('paper_height', 'check_height', 'paper_width', 'check_width', 'check_position', 'margin_top', 'margin_left')
    def _compute_check_margins(self):
        for record in self:
            margin_top = ((record.paper_height - record.check_height) / 2)
            margin_left = ((record.paper_width - record.check_width) / 2)
            if record.check_position == 'top':
                margin_top = min(margin_left, margin_top)
            elif record.check_position == 'bottom':
                margin_top = max(record.paper_height - record.check_height - margin_left, margin_top)
            elif record.check_position == 'custom':
                margin_top = record.margin_top
                margin_left = record.margin_left
            record.check_margin_top = margin_top
            record.check_margin_left = margin_left
