# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class L10n_ChQr_InvoiceWizard(models.TransientModel):
    '''
    Wizard :
    When multiple invoices are selected to be printed in the QR-Iban format,
    this wizard will appear if one or more invoice(s) could not be QR-printed (wrong format...)
    The user will then be able to print the invoices that couldn't be printed in the QR format in the normal format, or
    to see a list of those.
    The non-QR invoices will have a note logged in their chatter, detailing the reason of the failure.
    '''
    _name = 'l10n_ch.qr_invoice.wizard'
    _description = 'Handles problems occurring while creating multiple QR-invoices at once'

    nb_qr_inv = fields.Integer(readonly=True)
    nb_classic_inv = fields.Integer(readonly=True)
    qr_inv_text = fields.Text(readonly=True)
    classic_inv_text = fields.Text(readonly=True)

    @api.model
    def default_get(self, fields):
        # Extends 'base'.

        def determine_invoices_text(nb_inv, inv_format):
            '''
            Creates a sentence explaining nb_inv invoices could be printed in the inv_format format.
            '''
            if nb_inv == 0:
                return _("No invoice could be printed in the %s format.", inv_format)
            if nb_inv == 1:
                return _("One invoice could be printed in the %s format.", inv_format)
            return _("%(amount)s invoices could be printed in the %(format)s format.", amount=nb_inv, format=inv_format)

        if not self.env.context.get('active_ids'):
            raise UserError(_("No invoice was found to be printed."))

        invoices = self.env['account.move'].browse(self.env.context['active_ids'])
        companies = invoices.company_id
        if len(companies) != 1 or companies[0].country_code != 'CH':
            raise UserError(_("All selected invoices must belong to the same Switzerland company"))

        results = super().default_get(fields)
        dispatched_invoices = invoices._l10n_ch_dispatch_invoices_to_print()
        results.update({
            'nb_qr_inv': len(dispatched_invoices['qr']),
            'nb_classic_inv': len(dispatched_invoices['classic']),
            'qr_inv_text': determine_invoices_text(nb_inv=len(dispatched_invoices['qr']), inv_format="QR"),
            'classic_inv_text': determine_invoices_text(nb_inv=len(dispatched_invoices['classic']), inv_format="classic"),
        })
        return results

    def print_all_invoices(self):
        '''
        Triggered by the Print All button
        '''
        all_invoices_ids = self.env.context.get('inv_ids')
        return self.env.ref('account.account_invoices').report_action(all_invoices_ids)

    def action_view_faulty_invoices(self):
        '''
        Open a list view of all the invoices that could not be printed in the QR format.
        '''
        # Prints the error stopping the invoice from being QR-printed in the invoice's chatter.
        invoices = self.env['account.move'].browse(self.env.context['active_ids'])
        dispatched_invoices = invoices._l10n_ch_dispatch_invoices_to_print()
        faulty_invoices = dispatched_invoices['classic']

        # Log a message inside the chatter explaining why the invoice is faulty.
        for inv in faulty_invoices:
            error_msg = inv.partner_bank_id._get_error_messages_for_qr('ch_qr', inv.partner_id, inv.currency_id)
            if error_msg:
                inv.message_post(body=error_msg, message_type="comment")
        action_vals = {
            'name': _("Invalid Invoices"),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'context': {'create': False},
        }
        if len(faulty_invoices) == 1:
            action_vals.update({
                'view_mode': 'form',
                'res_id': faulty_invoices.id,
            })
        else:
            action_vals.update({
                'view_mode': 'list',
                'domain': [('id', 'in', faulty_invoices.ids)],
            })
        return action_vals
