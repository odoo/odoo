import re

from odoo import models
from odoo.exceptions import UserError

L10N_PT_GENERIC_NIF = '999999990'


def _l10n_pt_normalize_vat(vat):
    return re.sub(r'[^0-9A-Z]', '', (vat or '').upper())


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def _l10n_pt_get_vat(self):
        """
        The partner's tax number as the AT expects it in the QR code and the SAF-T: as collected,
        without the country prefix (QR spec v1.1 §4 field B, Portaria 302/2016 2.2.4), so a foreign
        number keeps its letters (NL000099998B57 gives 000099998B57). Empty without a number.
        """
        self.ensure_one()
        vat = _l10n_pt_normalize_vat(self.vat)
        return vat[2:] if re.match(r'^[A-Z]{2}', vat) else vat

    def _l10n_pt_has_nif(self):
        """Whether the partner was given a NIF: the generic 'Consumidor final' one does not count."""
        self.ensure_one()
        return bool(self.vat) and re.sub(r'[^0-9]', '', self.vat) != L10N_PT_GENERIC_NIF

    def _l10n_pt_partners_with_issued_documents(self):
        """
        The partners of ``self``'s commercial entities to which a PT document was issued, by any
        model built on the document mixin. Being numbered, such a document is a PT one, whatever the
        partner's own company.
        """
        partner_ids = set()
        for model_name in self.env['l10n_pt.at.series']._l10n_pt_document_models():
            # sudo: documents of every company count, whichever ones the user may see.
            for [partner] in self.env[model_name].sudo()._read_group(
                [
                    ('partner_id.commercial_partner_id', 'in', self.commercial_partner_id.ids),
                    ('l10n_pt_document_number', '!=', False),
                ],
                groupby=['partner_id'],
            ):
                partner_ids.add(partner.id)
        return self.browse(partner_ids)

    def write(self, vals):
        if 'vat' in vals or 'name' in vals:
            self._l10n_pt_check_identity_change(vals)
        return super().write(vals)

    def _l10n_pt_check_identity_change(self, vals):
        """
        Once documents were issued to a customer, its NIF can only be filled in when it was empty or
        generic (Despacho 8632/2014 3.3.3), and without a NIF its name cannot change (3.3.4).
        """
        new_vat = _l10n_pt_normalize_vat(vals.get('vat'))
        gives_nif = bool(new_vat) and re.sub(r'[^0-9]', '', new_vat) != L10N_PT_GENERIC_NIF
        vat_changes = self.filtered(lambda p: (
            'vat' in vals and p._l10n_pt_has_nif() and _l10n_pt_normalize_vat(p.vat) != new_vat
        ))
        name_changes = self.filtered(lambda p: (
            'name' in vals and p.name and vals['name'] != p.name and not p._l10n_pt_has_nif() and not gives_nif
        ))
        if not vat_changes and not name_changes:
            return
        issued_to = (vat_changes | name_changes)._l10n_pt_partners_with_issued_documents()
        if vat_changes.filtered(lambda p: p.commercial_partner_id in issued_to.commercial_partner_id):
            raise UserError(self.env._("You cannot change the VAT number of a partner that already has issued documents."))
        # The name printed on a document is that of its partner, or of the commercial entity above it.
        if name_changes.filtered(lambda p: p in issued_to or (p == p.commercial_partner_id and p in issued_to.commercial_partner_id)):
            raise UserError(self.env._("You cannot change the name of a partner without a VAT number that already has issued documents."))
