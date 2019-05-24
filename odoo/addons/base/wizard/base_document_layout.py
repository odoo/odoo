# -*- coding: utf-8 -*-

import logging
import base64
import json

from PIL import Image
from odoo import api, fields, models, tools
from odoo.tools.image import image_data_uri

def process_rgb(rgb):
    """
        Darkens the value if the value of a band is above a given threshold,
        then converts the tuple to a hex value
    """
    hex_list = []
    threshold = 200
    brightest = max(rgb)
    for color in range(3):
        value = rgb[color] / (brightest / threshold) if brightest > threshold else rgb[color]
        hex_list.append(hex(int(value)).split('x')[-1].zfill(2))
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
    preview_logo = fields.Binary(related='logo', string="Preview logo")
    report_header = fields.Text(related='company_id.report_header', readonly=False)
    report_footer = fields.Text(related='company_id.report_footer', readonly=False)
    paperformat_id = fields.Many2one(related='company_id.paperformat_id', readonly=False)
    external_report_layout_id = fields.Many2one(related='company_id.external_report_layout_id', readonly=False)

    font = fields.Selection(related='company_id.font', readonly=False)
    primary_color = fields.Char(related='company_id.primary_color', readonly=False)
    secondary_color = fields.Char(related='company_id.secondary_color', readonly=False)

    company_colors = fields.Char(compute="_compute_report_layout_id", string="Colors", readonly=False)
    previous_default = False

    report_layout_id = fields.Many2one('report.layout', compute="_compute_report_layout_id", readonly=False)
    preview = fields.Html(compute='_compute_preview')

    @api.depends('company_id')
    def _compute_report_layout_id(self):
        for wizard in self:
            wizard.report_layout_id = wizard.env["report.layout"].search([
                ('view_id.key', '=', wizard.company_id.external_report_layout_id.key)
            ])
            wizard.company_colors = json.dumps({
                'default': [wizard.report_layout_id.primary_color, wizard.report_layout_id.secondary_color],
                'values': [wizard.primary_color, wizard.secondary_color],
            })
            BaseDocumentLayout.previous_default = [wizard.report_layout_id.primary_color, wizard.report_layout_id.secondary_color]

    @api.depends('logo', 'font')
    def _compute_preview(self):
        """ compute a qweb based preview to display on the wizard """
        for wizard in self:
            ir_qweb = wizard.env['ir.qweb']
            colors = json.loads(wizard.company_colors)
            wizard.primary_color = colors['values'][0]
            wizard.secondary_color = colors['values'][1]
            wizard.preview = ir_qweb.render('web.layout_preview', {
                'company': wizard,
            })
    
    @api.onchange('company_colors')
    def onchange_company_colors(self):
        for wizard in self:
            values = json.loads(wizard.company_colors)['values']
            wizard.primary_color = values[0]
            wizard.secondary_color = values[1]
            wizard._compute_preview()

    @api.onchange('report_layout_id')
    def onchange_report_layout_id(self):
        for wizard in self:
            wizard.external_report_layout_id = wizard.report_layout_id.view_id
            
            values = json.loads(wizard.company_colors)['values']
            default = [wizard.report_layout_id.primary_color,
                       wizard.report_layout_id.secondary_color]

            if BaseDocumentLayout.previous_default == values:
                values = default
            BaseDocumentLayout.previous_default = default
            wizard.company_colors = json.dumps({
                'default': default,
                'values': values,
            })
            wizard._compute_preview()

    @api.onchange('logo')
    def onchange_logo(self):
        """ Identify dominant colors of the logo """
        for wizard in self:
            print('\n\n', wizard.logo, '\n\n')
            if not wizard.logo:
                return
            margin = 50
            white_threshold = 245

            # The "===" gives different base64 encoding a correct padding
            image = tools.base64_to_image(wizard.logo + "===").resize((40, 40))

            transparent = 'A' not in image.getbands()

            converted = image.convert('RGBA') if transparent else image
            w, h = image.size
            colors = []
            for color in converted.getcolors(w * h):
                if not(transparent and color[1][0] > white_threshold and
                       color[1][1] > white_threshold and color[1][2] > white_threshold) and color[1][3] > 0:
                    colors.append(color)

            primary, remaining = average_dominant_color(colors, margin)
            secondary = average_dominant_color(remaining, margin)[
                0] if len(remaining) > 0 else primary

            wizard.company_colors = json.dumps({
                'default': [wizard.report_layout_id.primary_color, wizard.report_layout_id.secondary_color],
                'values': [process_rgb(primary), process_rgb(secondary)],
            })
