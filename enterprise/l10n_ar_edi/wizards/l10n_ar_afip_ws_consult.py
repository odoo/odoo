# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools.zeep.helpers import serialize_object
import logging

_logger = logging.getLogger(__name__)


class L10nArAfipWsConsult(models.TransientModel):

    _name = 'l10n_ar_afip.ws.consult'
    _description = 'Consult Invoice Data in AFIP'

    number = fields.Integer(required=True)
    journal_id = fields.Many2one('account.journal', domain="[('l10n_ar_afip_pos_system', 'in', ['RAW_MAW', 'BFEWS', 'FEEWS'])]", required=True)
    document_type_id = fields.Many2one('l10n_latam.document.type')
    # Technical field used to compute the domain of the documents available for the given journal
    available_document_type_ids = fields.Many2many('l10n_latam.document.type', compute='_compute_available_document_types')
    consult_type = fields.Selection([('specific', 'Specific Invoice Number'), ('last', 'Get Last Invoice')], required=True,
        default="specific", string="Type", help="* Specific Invoice Number: consult all the invoice information in AFIP"
        " for the given number\n* Get Last Invoice: it connects to AFIP to get the last invoice number and show it in"
        " the number field")

    @api.onchange('journal_id')
    def onchange_journal(self):
        self.document_type_id = self.available_document_type_ids[0] if self.available_document_type_ids else False

    @api.depends('journal_id')
    def _compute_available_document_types(self):
        self.available_document_type_ids = False
        with_journal = self.filtered('journal_id')
        for rec in with_journal:
            rec.available_document_type_ids = self.env['l10n_latam.document.type'].search(
                rec.journal_id._get_journal_codes_domain()
            )
        remaining = self - with_journal
        remaining.available_document_type_ids = False

    def button_confirm(self):
        """ Recover infomation of an invoice that has already been authorized by AFIP.

        For auditing and troubleshooting purposes you can get the detailed information of an invoice number that has
        been previously sent to AFIP. You can also get the last number used in AFIP for a specific Document Type and
        POS Number as support for any possible issues on the sequence synchronization between Odoo and AFIP """
        self.ensure_one()
        pos_number = self.journal_id.l10n_ar_afip_pos_number
        afip_ws = self.journal_id.l10n_ar_afip_ws

        if not afip_ws:
            raise UserError(_('No AFIP WS selected on point of sale %s', self.journal_id.name))
        if not self.number:
            raise UserError(_('Please set the number you want to consult'))

        connection = self.journal_id.company_id._l10n_ar_get_connection(afip_ws)
        client, auth = connection._get_client()

        res = error = False
        # We need to call a different method for every webservice type and assemble the returned errors if they exist
        if afip_ws == 'wsfe':
            response = client.service.FECompConsultar(auth, {'CbteTipo': self.document_type_id.code, 'CbteNro': self.number, 'PtoVta': pos_number})
            res = response.ResultGet
            error = response.Errors
        elif afip_ws == 'wsfex':
            response = client.service.FEXGetCMP(auth, {'Cbte_tipo': self.document_type_id.code, 'Punto_vta': pos_number, 'Cbte_nro': self.number})
            res = response.FEXResultGet
            if response.FEXErr.ErrCode != 0 or response.FEXErr.ErrMsg != 'OK':
                error = response.FEXErr
        elif afip_ws == 'wsbfe':
            response = client.service.BFEGetCMP(auth, {"Tipo_cbte": self.document_type_id.code, "Punto_vta": pos_number, "Cbte_nro": self.number})
            res = response.BFEResultGet
            if response.BFEErr.ErrCode != 0 or response.BFEErr.ErrMsg != 'OK':
                error = '\n* Code %s: %s' % (response.BFEErr.ErrCode, response.BFEErr.ErrMsg)
            if response.BFEEvents.EventCode != 0 or response.BFEEvents.EventMsg:
                error += repr(response.BFEEvents)
        else:
            raise UserError(_('AFIP WS %s not implemented', afip_ws))

        title = _('Invoice number %s\n', self.number)
        if error:
            _logger.warning('%s\n%s' % (title, error))
            raise UserError(_("AFIP Errors: %(error)s", error=error))

        msg = ''
        data = serialize_object(res, dict)
        for key, value in data.items():
            msg += " * %s: %s\n" % (key, value or '')
        raise UserError(title + msg)

    @api.onchange('consult_type', 'journal_id', 'document_type_id')
    def onchange_last_invoice(self):
        """ Get the info of the last invoice we have in AFIP for this document tye and AFIP POS """
        if self.consult_type == 'last':
            if not self.journal_id or not self.document_type_id:
                raise UserError(_('Please set first the Journal and the Document Type before select this option'))
            self.number = self.journal_id._l10n_ar_get_afip_last_invoice_number(self.document_type_id)
        else:
            self.number = 0
