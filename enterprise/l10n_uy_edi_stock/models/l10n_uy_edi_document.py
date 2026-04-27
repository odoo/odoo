from odoo import api, fields, models
from odoo.exceptions import UserError


class L10nUyEdiDocument(models.Model):
    _inherit = "l10n_uy_edi.document"

    picking_id = fields.Many2one(comodel_name="stock.picking")

    @api.depends('picking_id.l10n_latam_document_number', 'picking_id.l10n_latam_document_type_id', 'picking_id.company_id', 'picking_id.partner_id')
    def _compute_from_origin(self):
        # EXTENDS 'l10n_uy_edi'
        super()._compute_from_origin()
        for doc in self:
            if doc.picking_id:
                doc.l10n_latam_document_number = doc.picking_id.l10n_latam_document_number
                doc.l10n_latam_document_type_id = doc.picking_id.l10n_latam_document_type_id
                doc.company_id = doc.picking_id.company_id
                doc.partner_id = doc.picking_id.partner_id

    @api.depends("l10n_latam_document_number")
    def _compute_display_name(self):
        """Display: 'Stock Picking Internal Sequence : Delivery Guide Number (if defined)'"""
        super()._compute_display_name()
        for edi_doc in self.filtered('l10n_latam_document_number'):
            edi_doc.display_name = f"({edi_doc.l10n_latam_document_type_id.doc_code_prefix} {edi_doc.l10n_latam_document_number})"

    def _get_origin_record(self):
        self.ensure_one()
        if self.move_id:
            return self.move_id
        if self.picking_id:
            return self.picking_id
        return False

    def _get_picking_uuid(self, origin_record):
        """UUID to identify picking (shortcut for testing env unicity)"""
        origin_record.ensure_one()
        res = origin_record._name + "-" + str(origin_record.id)
        if origin_record.company_id.l10n_uy_edi_ucfe_env == "testing":
            res = "sp" + str(origin_record.id) + "-" + origin_record.env.cr.dbname
        return res[:50]

    def _get_cfe_picking_tag(self, picking):
        """Get CFE tag for stock picking"""
        picking.ensure_one()
        tags = {"181": "eRem"}
        tag = tags.get(picking.l10n_latam_document_type_id.code)
        if not tag:
            raise UserError(self.env._("You need to define the origin record of this EDI document"))
        return tag

    def _get_pdf(self):
        # EXTEND from l10n_uy_edi
        """Get PDF for the document"""
        return super()._get_pdf()

    def action_update_dgi_state(self):
        pickings = self.filtered(lambda x: x.picking_id)
        for edi_doc in pickings:
            result = edi_doc._ucfe_inbox("360", {"Uuid": edi_doc.uuid})
            edi_doc._update_cfe_state(result)
        return super(L10nUyEdiDocument, self - pickings).action_update_dgi_state()
