 #-*- coding: utf-8 -*-

from odoo import api, fields, models, _

class FastReportDesigner(models.TransientModel):

    _name = 'fastreport.designer'

    fr_design_url = fields.Char('FastReport Designer Url',default="http://www.baidu.com",readonly=True)

    iframe = fields.Html('Embedded Webpage', compute='_compute_iframe', sanitize=False, strip_style=False ,readonly=True)

    framed_page_rendered = fields.Html('fastreport designer',readonly=True)

    @api.model
    def _compute_iframe(self):
        for frdesgin in self:
            url = frdesgin.fr_design_url
            template = self.env.ref('fastreport_odoo.framed_page')
            frdesgin.iframe = template._render({ 'url' : url })
