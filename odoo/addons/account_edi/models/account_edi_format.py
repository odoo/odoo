# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.tools.pdf import OdooPdfFileReader
from odoo.osv import expression
from odoo.tools import html_escape
from odoo.exceptions import RedirectWarning

from lxml import etree
from struct import error as StructError
import base64
import io
import logging
import pathlib
import re

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

        if not edi_formats:
            return edi_formats

        # activate by default on journal
        if not self.pool.loaded:
            # The registry is not totally loaded. We cannot yet recompute the field on jourals as
            # The helper methods aren't yet overwritten by all installed `l10n_` modules.
            # Delay it in the register hook
            self.pool._delay_compute_edi_format_ids = True
        else:
            journals = self.env['account.journal'].search([])
            journals._compute_edi_format_ids()

        # activate cron
        if any(edi_format._needs_web_services() for edi_format in edi_formats):
            self.env.ref('account_edi.ir_cron_edi_network').active = True

        return edi_formats

    def _register_hook(self):
        if hasattr(self.pool, "_delay_compute_edi_format_ids"):
            del self.pool._delay_compute_edi_format_ids
            journals = self.env['account.journal'].search([])
            journals._compute_edi_format_ids()

        return super()._register_hook()

    ####################################################
    # Export method to override based on EDI Format
    ####################################################

    def _get_move_applicability(self, move):
        """ Core function for the EDI processing: it first checks whether the EDI format is applicable on a given
        move, if so, it then returns a dictionary containing the functions to call for this move.

        :return: dict mapping str to function (callable)
        * post:             function called for edi.documents with state 'to_send' (post flow)
        * cancel:           function called for edi.documents with state 'to_cancel' (cancel flow)
        * post_batching:    function returning the batching key for the post flow
        * cancel_batching:  function returning the batching key for the cancel flow
        * edi_content:      function called when computing the edi_content for an edi.document
        """
        self.ensure_one()

    def _needs_web_services(self):
        """ Indicate if the EDI must be generated asynchronously through to some web services.

        :return: True if such a web service is available, False otherwise.
        """
        self.ensure_one()
        return False

    def _is_compatible_with_journal(self, journal):
        """ Indicate if the EDI format should appear on the journal passed as parameter to be selected by the user.
        If True, this EDI format will appear on the journal.

        :param journal: The journal.
        :returns:       True if this format can appear on the journal, False otherwise.
        """
        # TO OVERRIDE
        self.ensure_one()
        return journal.type == 'sale'

    def _is_enabled_by_default_on_journal(self, journal):
        """ Indicate if the EDI format should be selected by default on the journal passed as parameter.
        If True, this EDI format will be selected by default on the journal.

        :param journal: The journal.
        :returns:       True if this format should be enabled by default on the journal, False otherwise.
        """
        return True

    def _check_move_configuration(self, move):
        """ Checks the move and relevant records for potential error (missing data, etc).

        :param move:    The move to check.
        :returns:       A list of error messages.
        """
        # TO OVERRIDE
        return []

    ####################################################
    # Import methods to override based on EDI Format
    ####################################################

    def _prepare_invoice_report(self, pdf_writer, edi_document):
        """
        Prepare invoice report to be printed.
        :param pdf_writer: The pdf writer with the invoice pdf content loaded.
        :param edi_document: The edi document to be added to the pdf file.
        """
        # TO OVERRIDE
        self.ensure_one()

    ####################################################
    # Other helpers
    ####################################################

    @api.model
    def _format_error_message(self, error_title, errors):
        bullet_list_msg = ''.join('<li>%s</li>' % html_escape(msg) for msg in errors)
        return '%s<ul>%s</ul>' % (error_title, bullet_list_msg)
