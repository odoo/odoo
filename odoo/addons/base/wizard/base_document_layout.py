# -*- coding: utf-8 -*-

import logging
import base64

from PIL import Image
from odoo import api, fields, models, tools
from odoo.tools.image import image_data_uri

_logger = logging.getLogger(__name__)


def rgb_to_hex(rgb):
    hex_list = []
    for color in range(3):
        hex_list.append(hex(rgb[color]).split('x')[-1].zfill(2))
    return '#' + ''.join(hex_list)


def average_dominant_color(colors, margin):
    dominant_color = max(colors)
    dominant_set = [dominant_color]
    colors.remove(dominant_color)
    remaining = []

    for color in colors:
        # Test similarity (r, g and b are within <margin> of dominant color)
        if (color[1][0] < dominant_color[1][0] + margin and
            color[1][0] > dominant_color[1][0] - margin and
            color[1][1] < dominant_color[1][1] + margin and
            color[1][1] > dominant_color[1][1] - margin and
            color[1][2] < dominant_color[1][2] + margin and
                color[1][2] > dominant_color[1][2] - margin):
            dominant_set.append(color)
        else:
            remaining.append(color)

    final_avg = []
    for band in range(3):
        avg = 0
        total = 0
        for color in dominant_set:
            avg += color[0] * color[1][band]
            total += color[0]
        final_avg.append(round(avg / total))

    return final_avg, remaining

class BaseDocumentLayout(models.TransientModel):
    """
        Customise the company document layout and display a live preview
    """

    _name = 'base.document.layout'
    _description = 'Company Document Layout'

    company_id = fields.Many2one('res.company', required=True)

    logo = fields.Binary(related='company_id.logo', readonly=False)
    preview_logo = fields.Binary(related='logo', readonly=False, string="Preview logo")
    report_header = fields.Text(related='company_id.report_header', readonly=False)
    report_footer = fields.Text(related='company_id.report_footer', readonly=False)
    paperformat_id = fields.Many2one(related='company_id.paperformat_id', readonly=False)
    external_report_layout_id = fields.Many2one(
        related='company_id.external_report_layout_id', readonly=False)

    font = fields.Selection(related='company_id.font', readonly=False)
    primary_color = fields.Char(related='company_id.primary_color', readonly=False)
    secondary_color = fields.Char(related='company_id.secondary_color', readonly=False)

    custom_primary = fields.Boolean(compute="_compute_custom_colors", default=False)
    custom_secondary = fields.Boolean(compute="_compute_custom_colors", default=False)

    report_layout_id = fields.Many2one('report.layout', compute="_compute_report_layout_id", readonly=False)
    preview = fields.Html(compute='_compute_preview')

    @api.depends('company_id')
    def _compute_report_layout_id(self):
        for wizard in self:
            wizard.report_layout_id = wizard.env["report.layout"].search([
                ('view_id.key', '=', wizard.company_id.external_report_layout_id.key)
            ])

    @api.depends('primary_color', 'secondary_color')
    def _compute_custom_colors(self):
        for wizard in self:
            wizard.custom_primary = wizard.primary_color != wizard.report_layout_id.primary_color
            wizard.custom_secondary = wizard.secondary_color != wizard.report_layout_id.secondary_color

    @api.depends('logo', 'font')
    def _compute_preview(self):
        """ compute a qweb based preview to display on the wizard """
        for wizard in self:
            ir_qweb = wizard.env['ir.qweb']
            wizard.preview = ir_qweb.render('web.layout_preview', {
                'company': wizard,
            })

    @api.onchange('primary_color', 'secondary_color')
    def onchange_colors(self):
        for wizard in self:
            wizard._compute_preview()

    @api.onchange('report_layout_id')
    def onchange_report_layout_id(self):
        for wizard in self:
            is_primary_default = not wizard.custom_primary
            is_secondary_default = not wizard.custom_secondary

            if is_primary_default:
                wizard.primary_color = wizard.report_layout_id.primary_color
            if is_secondary_default:
                wizard.secondary_color = wizard.report_layout_id.secondary_color
            wizard.external_report_layout_id = wizard.report_layout_id.view_id
            wizard._compute_preview()

    @api.multi
    def reset_colors(self):
        """ set the colors to the current layout default colors """
        for wizard in self:
            wizard.primary_color = wizard.report_layout_id.primary_color
            wizard.secondary_color = wizard.report_layout_id.secondary_color

    @api.multi
    def detect_colors(self):
        """ Identify dominant colors of the logo """
        for wizard in self:
            margin = 80

            # Compute image
            image = tools.base64_to_image(wizard.logo).resize((40, 40))

            transparent = 'A' not in image.getbands()

            converted = image.convert('RGBA') if transparent else image
            w, h = image.size
            colors = []
            for color in converted.getcolors(w * h):
                if not(transparent and color[1][0] > 240 and color[1][1] > 240 and color[1][2] > 240) and color[1][3] > 0:
                    colors.append(color)

            primary, remaining = average_dominant_color(colors, margin)
            secondary = average_dominant_color(remaining, margin)[0] if len(remaining) > 0 else primary

            wizard.primary_color = rgb_to_hex(primary)
            wizard.secondary_color = rgb_to_hex(secondary)

    @api.multi
    def download_preview(self):
        # TODO download preview
        for wizard in self:
            pass
            # ReportController = next(x for x in http.controllers_per_module.get(
            #     'web') if x[0] == 'odoo.addons.web.controllers.main.ReportController')[1]
            # ReportController.report_download(
            #     ["/report/pdf/account.report_invoice_with_payments/3", "qweb-pdf"])
