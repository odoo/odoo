# -*- coding: utf-8 -*-

from odoo import api, fields, models, tools

DEFAULT_PRIMARY = '#000000'
DEFAULT_SECONDARY = '#000000'


class BaseDocumentLayout(models.TransientModel):
    """
    Customise the company document layout and display a live preview
    """

    _name = 'base.document.layout'
    _description = 'Company Document Layout'

    company_id = fields.Many2one(
        'res.company', default=lambda self: self.env.company, required=True)

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
    logo_primary_color = fields.Char()
    logo_secondary_color = fields.Char()

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
                default_report_layout = default_report_layout or default_report_layout.search([
                ], limit=1)
                wizard_layout = default_report_layout
            wizard.report_layout_id = wizard_layout

            if wizard.logo:
                wizard_for_image = wizard
                if wizard._context.get('bin_size'):
                    wizard_for_image = wizard.with_context(bin_size=False)
                wizard.logo_primary_color, wizard.logo_secondary_color = wizard_for_image._parse_logo_colors()
            if not wizard.primary_color:
                wizard.primary_color = wizard.logo_primary_color or DEFAULT_PRIMARY
            if not wizard.secondary_color:
                wizard.secondary_color = wizard.logo_secondary_color or DEFAULT_SECONDARY

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
            logo_primary = wizard.logo_primary_color or ''
            logo_secondary = wizard.logo_secondary_color or ''
            # Force lower case on color to ensure that FF01AA == ff01aa
            wizard.custom_colors = wizard.logo and wizard.primary_color and wizard.secondary_color and not(
                wizard.primary_color.lower() == logo_primary.lower() and
                wizard.secondary_color.lower() == logo_secondary.lower())

    @api.onchange('custom_colors')
    def onchange_custom_colors(self):
        for wizard in self:
            if wizard.logo and not wizard.custom_colors:
                wizard.primary_color = wizard.logo_primary_color or DEFAULT_PRIMARY
                wizard.secondary_color = wizard.logo_secondary_color or DEFAULT_SECONDARY
                
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

        :return colors: hex values of primary and secondary colors
        """
        self.ensure_one()
        logo = logo or self.logo
        if not logo:
            return False, False

        # The "===" gives different base64 encoding a correct padding
        logo += b'===' if type(logo) == bytes else '==='
        try:
            # Catches exceptions caused by logo not being an image
            image = tools.base64_to_image(logo)
        except:
            return False, False

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

        if not colors:  # May happen when the whole image is white
            return False, False
        primary, remaining = tools.average_dominant_color(colors)
        secondary = tools.average_dominant_color(
            remaining)[0] if len(remaining) > 0 else primary

        # Lightness and saturation are calculated here.
        # - If both colors have a similar lightness, the most colorful becomes primary
        # - When the difference in lightness is too great, the brightest color becomes primary
        l_primary = tools.get_lightness(primary)
        l_secondary = tools.get_lightness(secondary)
        if (l_primary < 0.2 and l_secondary < 0.2) or (l_primary >= 0.2 and l_secondary >= 0.2):
            s_primary = tools.get_saturation(primary)
            s_secondary = tools.get_saturation(secondary)
            if s_primary < s_secondary:
                primary, secondary = secondary, primary
        elif l_secondary > l_primary:
            primary, secondary = secondary, primary

        return tools.rgb_to_hex(primary), tools.rgb_to_hex(secondary)

    @api.onchange('report_layout_id')
    def onchange_report_layout_id(self):
        for wizard in self:
            wizard.external_report_layout_id = wizard.report_layout_id.view_id
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
            # at that point wizard.logo has been assigned the value present in DB
            logo_same = company.logo == logo
            wizard.logo = logo
            if not logo:
                wizard.logo_primary_color, wizard.logo_secondary_color = False, False
                wizard._compute_custom_colors()
            if logo_same and company.primary_color and company.secondary_color:
                continue

            wizard.logo_primary_color, wizard.logo_secondary_color = wizard._parse_logo_colors()
            if wizard.logo_primary_color:
                wizard.primary_color = wizard.logo_primary_color
            if wizard.logo_secondary_color:
                wizard.secondary_color = wizard.logo_secondary_color

    @api.model
    def action_open_base_document_layout(self, action_ref=None):
        if not action_ref:
            action_ref = 'base.action_base_document_layout_configurator'
        return self.env.ref(action_ref).read()[0]

    def document_layout_save(self):
        # meant to be overridden
        pass
