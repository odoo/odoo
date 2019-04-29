# -*- coding: utf-8 -*-

import logging
import base64

from odoo import api, fields, models
from odoo.tools.image import image_data_uri

_logger = logging.getLogger(__name__)

class BaseDocumentLayout(models.TransientModel):
    """
        Customise the company document layout and display a live preview
    """

    _name = 'base.document.layout'
    _description = 'Company Document Layout'

    company_id = fields.Many2one('res.company', required=True)

    logo = fields.Binary(related='company_id.logo', readonly=False)
    preview_logo = fields.Binary(related='logo', readonly=False)
    report_header = fields.Text(related='company_id.report_header', readonly=False)
    report_footer = fields.Text(related='company_id.report_footer', readonly=False)
    paperformat_id = fields.Many2one(related='company_id.paperformat_id', readonly=False)
    external_report_layout_id = fields.Many2one(
        related='company_id.external_report_layout_id', readonly=False)

    font = fields.Selection(related='company_id.font', readonly=False)
    primary_color = fields.Char(related='company_id.primary_color', readonly=False)
    secondary_color = fields.Char(related='company_id.secondary_color', readonly=False)

    report_layout_id = fields.Many2one('report.layout', compute="_compute_report_layout_id", readonly=False)
    use_default_colors = fields.Boolean(compute="_compute_use_default_colors")
    preview = fields.Html(compute='_compute_preview')
    reset_link = fields.Boolean()

    @api.depends('company_id')
    def _compute_report_layout_id(self):
        for wizard in self:
            wizard.report_layout_id = wizard.env["report.layout"].search([
                ('view_id.key', '=', wizard.company_id.external_report_layout_id.key)
            ])

    @api.depends('company_id')
    def _compute_use_default_colors(self):
        for wizard in self:
            wizard.use_default_colors = not(wizard.primary_color and wizard.secondary_color)

    @api.onchange('reset_link')
    def reset_colors(self):
        """ set the colors to the current layout default colors """
        for wizard in self:
            wizard.primary_color = wizard.report_layout_id.primary_color
            wizard.secondary_color = wizard.report_layout_id.secondary_color

    @api.onchange('primary_color', 'secondary_color')
    def onchange_colors(self):
        for wizard in self:
            if wizard.env.context.get('user_selected', False):  # color change caused by user
                wizard.use_default_colors = False
            else:                                               # color change caused by reset_colors()
                wizard.use_default_colors = True
            wizard._compute_preview()

    @api.onchange('report_layout_id')
    def onchange_report_layout_id(self):
        for wizard in self:
            if wizard.use_default_colors:
                wizard.reset_colors()
            wizard.external_report_layout_id = wizard.report_layout_id.view_id
            wizard._compute_preview()

    @api.depends('logo', 'font')
    def _compute_preview(self):
        """ compute a qweb based preview to display on the wizard """
        for wizard in self:
            ir_qweb = wizard.env['ir.qweb']
            wizard.preview = ir_qweb.render('web.layout_preview', {
                'company'       : wizard,
            })
