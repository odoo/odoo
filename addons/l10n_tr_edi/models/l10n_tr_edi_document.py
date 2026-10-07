from odoo import fields, models


class L10n_Tr_EdiDocument(models.Model):
    _name = 'l10n_tr_edi.document'
    _description = "Turkish e-Document exchanged with the GİB"
    _order = 'datetime DESC, id DESC'
    _check_company_auto = True

    move_id = fields.Many2one(
        comodel_name='account.move',
        index='btree_not_null',
        check_company=True,
        ondelete='cascade',
    )
    company_id = fields.Many2one(comodel_name='res.company', required=True, index=True)
    document_type = fields.Selection(
        selection=[
            ('einvoice', "e-Invoice"),
            ('earchive', "e-Archive"),
            ('commercial_response', "Commercial Invoice Response"),
        ],
        required=True,
    )
    provider = fields.Selection(
        selection=[],
        help="The integrator the document was sent through. It is kept even if the company changes provider, "
        "so the document keeps being synchronized with the one that holds it.",
    )
    name = fields.Char(string="Document Number", copy=False)
    uuid = fields.Char(string="UUID", copy=False)
    state = fields.Selection(
        selection=[
            ('draft', "Draft"),
            ('sent', "Sent"),
            ('waiting', "Waiting for GİB"),
            ('accepted', "Accepted"),
            ('accepted_automatically', "Accepted Automatically"),
            ('rejected', "Rejected"),
            ('error', "Error"),
            ('cancelled', "Cancelled"),
        ],
        required=True,
    )
    datetime = fields.Datetime(default=fields.Datetime.now, required=True)
    message = fields.Text()
    attachment_id = fields.Many2one(comodel_name='ir.attachment', string="XML File")

    _company_uuid_unique = models.Constraint(
        'UNIQUE(company_id, uuid)',
        "A company cannot have two e-Documents with the same UUID.",
    )

    def action_download(self):
        """ Download the XML file linked to the document. """
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{self.attachment_id.id}?download=true',
        }
