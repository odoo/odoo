# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api
from odoo.tools.pdf import OdooPdfFileReader, OdooPdfFileWriter
from odoo.osv import expression
from odoo.tools import html_escape

from lxml import etree
import base64
import io
import logging
import pathlib

_logger = logging.getLogger(__name__)


class AccountEdiFormat(models.Model):
    _name = 'account.edi.format'
    _description = 'EDI format'

    name = fields.Char()
    code = fields.Char(required=True)

    _sql_constraints = [
        ('unique_code', 'unique (code)', 'This code already exists')
    ]


    ####################################################
    # Low-level methods
    ####################################################

    @api.model_create_multi
    def create(self, vals_list):
        edi_formats = super().create(vals_list)

        # activate by default on picking_type
        picking_types = self.env['stock.picking.type'].search([])
        for picktype in picking_types:
            for edi_format in edi_formats:
                if edi_format._is_compatible_with_picking_type(picktype):
                    picktype.edi_format_ids += edi_format

        # activate cron
        if any(edi_format._needs_web_services() for edi_format in edi_formats):
            self.env.ref('account_edi.ir_cron_edi_network').active = True

        return edi_formats

    ####################################################
    # Export method to override based on EDI Format
    ####################################################

    def _is_required_for_picking(self, picking):
        """ Indicate if this EDI must be generated for the picking passed as parameter.

                :param picking: A picking having the right type
                :returns:       True if the EDI must be generated, False otherwise.
                """
        # TO OVERRIDE
        self.ensure_one()
        return False

    def _is_compatible_with_picking_type(self, picktype):
        """ Indicate if the EDI format should appear on the journal passed as parameter to be selected by the user.
        If True, this EDI format will be selected by default on the journal.

        :param journal: The journal.
        :returns:       True if this format can be enabled by default on the journal, False otherwise.
        """
        # TO OVERRIDE
        self.ensure_one()
        return picktype.code == 'outgoing'

    def _check_picking_configuration(self, move):
        """ Checks the move and relevant records for potential error (missing data, etc).

        :param invoice: The move to check.
        :returns:       A list of error messages.
        """
        # TO OVERRIDE
        return []

    def _post_picking_edi(self, pickings, test_mode=False):
        """ Create the file content representing the invoice (and calls web services if necessary).

        :param pickings:    A list of pickings to post.
        :param test_mode:   A flag indicating the EDI should only simulate the EDI without sending data.
        :returns:           A dictionary with the invoice as key and as value, another dictionary:
        * attachment:       The attachment representing the invoice in this edi_format if the edi was successfully posted.
        * error:            An error if the edi was not successfully posted.
        * blocking_level:    (optional, requires account_edi_extended) How bad is the error (how should the edi flow be blocked ?)
        """
        # TO OVERRIDE
        self.ensure_one()
        return {}

    def _cancel_picking_edi(self, pickings, test_mode=False):
        """Calls the web services to cancel the invoice of this document.

        :param invoices:    A list of invoices to cancel.
        :param test_mode:   A flag indicating the EDI should only simulate the EDI without sending data.
        :returns:           A dictionary with the invoice as key and as value, another dictionary:
        * success:          True if the invoice was successfully cancelled.
        * error:            An error if the edi was not successfully cancelled.
        * blocking_level:    (optional, requires account_edi_extended) How bad is the error (how should the edi flow be blocked ?)
        """
        # TO OVERRIDE
        self.ensure_one()
        return {picking: {'success': True} for picking in pickings}  # By default, cancel succeeds doing nothing.
