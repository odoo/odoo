from odoo import fields, models


class L10nGtEdiDocument(models.Model):
    _name = 'l10n_gt_edi.document'
    _description = "Guatemalan documents that needs to transit outside of Odoo"
    _order = 'datetime DESC, id DESC'

    invoice_id = fields.Many2one(comodel_name='account.move')
    state = fields.Selection(
        selection=[
            ('invoice_sent', 'Sent'),
            ('invoice_sending_failed', 'Sending Failed'),
        ],
        string='GT Status',
        required=True,
        help="Sent -> Successfully sent to the SAT.\n"
             "Sending Failed -> Sending error or validation error from the SAT.",
    )
    datetime = fields.Datetime(default=fields.Datetime.now, required=True)
    attachment_id = fields.Many2one(comodel_name='ir.attachment', readonly=True)
    message = fields.Char()
    uuid = fields.Char()
    series = fields.Char()
    serial_number = fields.Char()
    certification_date = fields.Char()

    def action_download_file(self):
        """ Download the XML file linked to the document.

        :return: An action to download the attachment.
        """
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{self.attachment_id.id}?download=true',
        }
