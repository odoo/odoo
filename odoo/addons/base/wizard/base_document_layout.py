# -*- coding: utf-8 -*-

from odoo import api, fields, models, tools


def average_dominant_color(colors, mitigate=200, hard_mitigate=160, max_margin=140):
    """
    This function is used to calculate the average dominant color

    There are 5 steps :
        1) Select dominant colors (highest count), isolate its values and remove
           it from the current color set.
        2) Set margins according to the prevalence of the dominant color.
        3) Evaluate the colors. Similar colors are grouped in the dominant set
           while others are put in the "remaining" list.
        4) Calculate the average color for the dominant set. This is done by
           averaging each band and joining them into a tuple.
        5) Mitigate final average and convert it to hex

    :param colors: list of tuples having:
        [0] color count in the image
        [1] actual color: tuple(R, G, B, A)
    :param mitigate: maximum value a band can reach
    :param hard_mitigate: used instead of mitigate when the color is too bright
    :param max_margin: maximum difference from one of the dominant values
    :returns: a tuple with two items:
        [0] the average color of the dominant set as: tuple(R, G, B)
        [1] list of remaining colors, used to evaluate subsequent dominant colors
    """
    dominant_color = max(colors)
    dominant_rgb = dominant_color[1][:3]
    dominant_set = [dominant_color]
    remaining = []

    margins = [max_margin * (1 - dominant_color[0] /
                             sum([col[0] for col in colors]))] * 3

    colors.remove(dominant_color)

    for color in colors:
        rgb = color[1]
        if (rgb[0] < dominant_rgb[0] + margins[0] and rgb[0] > dominant_rgb[0] - margins[0] and
            rgb[1] < dominant_rgb[1] + margins[1] and rgb[1] > dominant_rgb[1] - margins[1] and
                rgb[2] < dominant_rgb[2] + margins[2] and rgb[2] > dominant_rgb[2] - margins[2]):
            dominant_set.append(color)
        else:
            remaining.append(color)

    dominant_avg = []
    for band in range(3):
        avg = total = 0
        for color in dominant_set:
            avg += color[0] * color[1][band]
            total += color[0]
        dominant_avg.append(int(avg / total))

    dominant_hex = []
    threshold = mitigate if sum(dominant_avg) < 650 else hard_mitigate
    brightest = max(dominant_avg)
    for color in range(3):
        value = dominant_avg[color] / (brightest /
                                       threshold) if brightest > threshold else dominant_avg[color]
        dominant_hex.append(hex(int(value)).split('x')[-1].zfill(2))

    return '#' + ''.join(dominant_hex), remaining


class BaseDocumentLayout(models.TransientModel):
    """
    Customise the company document layout and display a live preview
    """

    _name = 'base.document.layout'
    _description = 'Company Document Layout'

    company_id = fields.Many2one('res.company', default=lambda self: self.env.company_id, required=True)

    logo = fields.Binary(related='company_id.logo', readonly=False)
    preview_logo = fields.Binary(related='logo', string="Preview logo")
    report_header = fields.Text(related='company_id.report_header', readonly=False)
    report_footer = fields.Text(related='company_id.report_footer', readonly=False)
    paperformat_id = fields.Many2one(related='company_id.paperformat_id', readonly=False)
    external_report_layout_id = fields.Many2one(related='company_id.external_report_layout_id', readonly=False)

    font = fields.Selection(related='company_id.font', readonly=False)
    primary_color = fields.Char(related='company_id.primary_color', readonly=False)
    secondary_color = fields.Char(related='company_id.secondary_color', readonly=False)

    custom_colors = fields.Boolean(compute="_compute_custom_colors", readonly=False)

    report_layout_id = fields.Many2one('report.layout', compute="_compute_report_layout_id", readonly=False)
    preview = fields.Html(compute='_compute_preview')

    @api.depends('company_id')
    def _compute_report_layout_id(self):
        default_report_layout = self.env['report.layout']
        for wizard in self:
            wizard_layout = wizard.env["report.layout"].search([
                ('view_id.key', '=', wizard.company_id.external_report_layout_id.key)
            ])
            if not wizard_layout:
                default_report_layout = default_report_layout or default_report_layout.search([], limit=1)
                wizard_layout = default_report_layout
            wizard.report_layout_id = wizard_layout
            primary = wizard.primary_color or wizard.report_layout_id.primary_color
            secondary = wizard.secondary_color or wizard.report_layout_id.secondary_color

            if wizard.logo and (not wizard.primary_color and not wizard.secondary_color):
                wizard_for_image = wizard
                if wizard._context.get('bin_size'):
                    wizard_for_image = wizard.with_context(bin_size=False)
                primary, secondary = wizard_for_image._parse_logo_colors()

            wizard.primary_color = primary
            wizard.secondary_color = secondary

    @api.depends('logo', 'font')
    def _compute_preview(self):
        """ compute a qweb based preview to display on the wizard """
        for wizard in self:
            ir_qweb = wizard.env['ir.qweb']
            wizard.preview = ir_qweb.render('base.layout_preview', {
                'company': wizard,
            })

    @api.depends('primary_color', 'secondary_color')
    def _compute_custom_colors(self):
        for wizard in self:
            wizard.custom_colors = wizard.primary_color and wizard.secondary_color and not(
                wizard.primary_color.lower() == wizard.report_layout_id.primary_color.lower() and
                wizard.secondary_color.lower() == wizard.report_layout_id.secondary_color.lower())

    @api.onchange('custom_colors')
    def onchange_custom_colors(self):
        for wizard in self:
            if not wizard.custom_colors:
                wizard.primary_color = wizard.report_layout_id.primary_color
                wizard.secondary_color = wizard.report_layout_id.secondary_color

    @api.onchange('primary_color', 'secondary_color')
    def onchange_company_colors(self):
        for wizard in self:
            wizard._compute_custom_colors()
            wizard._compute_preview()

    def _parse_logo_colors(self, logo=None, white_threshold=225):
        """
        Identifies dominant colors

        First resizes the original image to improve performance, then discards
        transparent colors and white-ish colors, then calls the averaging
        method twice to evaluate both primary and secondary colors.

        :param logo: alternate logo to process
        :param white_threshold: arbitrary value defining the maximum value a color can reach
        """
        self.ensure_one()
        logo = logo or self.logo
        if not logo:
            return None, None

        # The "===" gives different base64 encoding a correct padding
        if isinstance(logo, bytes):
            logo = logo + b'==='
        else:
            # In onchange
            logo = logo + '==='
        try:
            # Catches exceptions caused by logo not being an image
            image = tools.base64_to_image(logo)
        except:
            return None, None

        base_w, base_h = image.size
        w = int(50 * base_w / base_h)
        h = 50

        # Converts to RGBA if no alpha detected
        image_converted = image.convert(
            'RGBA') if 'A' not in image.getbands() else image
        image_resized = image_converted.resize((w, h))

        colors = []
        for color in image_resized.getcolors(w * h):
            if not(color[1][0] > white_threshold and
                color[1][1] > white_threshold and
                color[1][2] > white_threshold) and color[1][3] > 0:
                colors.append(color)

        primary, remaining = average_dominant_color(colors)
        secondary = average_dominant_color(
            remaining)[0] if len(remaining) > 0 else primary

        return primary, secondary

    @api.onchange('report_layout_id')
    def onchange_report_layout_id(self):
        for wizard in self:
            wizard.external_report_layout_id = wizard.report_layout_id.view_id

            if not wizard.custom_colors:
                wizard.primary_color = wizard.report_layout_id.primary_color
                wizard.secondary_color = wizard.report_layout_id.secondary_color
            wizard._compute_preview()

    @api.onchange('logo')
    def onchange_logo(self):
        for wizard in self:
            # Trick to:
            # - test the new logo is different from company's
            # - Avoid the cache miss on company.logo to erase the new logo
            # It is admitted that if the user puts the original image back, it won't change colors
            logo = wizard.logo
            company = wizard.company_id
            logo_same = company.logo == logo  # at that point wizard.logo has been assigned the value present in DB
            wizard.logo = logo
            if not logo or (logo_same and company.primary_color and company.secondary_color):
                continue

            wizard.primary_color, wizard.secondary_color = wizard._parse_logo_colors()

    @api.model
    def action_open_base_document_layout(self, action_ref=None):
        if not action_ref:
            action_ref = 'base.action_base_document_layout_configurator'
        return self.env.ref(action_ref).read()[0]

    def document_layout_save(self):
        # meant to be overriden
        pass
