# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api
from odoo.exceptions import UserError
from odoo.tools.pdf import OdooPdfFileReader, OdooPdfFileWriter
from odoo.osv import expression

from lxml import etree
import base64
import io
import logging

_logger = logging.getLogger(__name__)


class EdiFormat(models.Model):
    _inherit = 'edi.format'


    ####################################################
    # Low-level methods
    ####################################################

    @api.model_create_multi
    def create(self, vals_list):
        edi_formats = super().create(vals_list)

        # activate by default on journal
        journals = self.env['account.journal'].search([])
        journals._compute_edi_format_ids()

        # activate cron
        if any(edi_format._needs_web_services() for edi_format in edi_formats):
            self.env.ref('account_edi.ir_cron_edi_network').active = True

        return edi_formats
