from odoo import fields, models, _, api
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    _inherit = 'res.partner'

    l10n_gt_edi_phrase_ids = fields.Many2many(
        comodel_name="l10n_gt_edi.phrase",
        string="Phrases",
    )
    l10n_gt_edi_consignatory_code = fields.Char(
        string="Consignatory Code",
        size=17,
    )

    @api.constrains('vat', 'l10n_latam_identification_type_id')
    def check_vat(self):
        """
        This check ensures that Guatemalan partner with CUI identification type gets a
        special validation check which is not provided by the standard `stdnum` validator.
        """
        # EXTENDS l10n_latam_base
        partner_with_cui_number = self.filtered(lambda p: all((
            p.country_code == 'GT',
            p.vat,
            p.l10n_latam_identification_type_id == self.env.ref('l10n_gt_edi.it_cui'),
        )))
        for partner in partner_with_cui_number:
            partner._l10n_gt_edi_check_cui_number()

        return super(ResPartner, self - partner_with_cui_number).check_vat()

    def _l10n_gt_edi_check_cui_number(self):
        self.ensure_one()
        if not self.vat or len(self.vat) < 9:
            raise ValidationError(_("The provided CUI number is too short."))

        try:
            cui_sum = sum(int(a) * b for a, b in zip(self.vat[:8], range(2, 10)))
            cui_res = '0123456789K'[(cui_sum % 11)]
            if self.vat[8] != cui_res:
                raise ValidationError(_("The provided CUI number does not pass the validation."))
        except ValueError:
            raise ValidationError(_("The provided CUI number contains invalid characters."))
