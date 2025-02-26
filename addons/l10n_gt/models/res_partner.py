import stdnum.gt
from odoo import models, api, _
from odoo.exceptions import ValidationError


class ResPartner(models.Model):

    _inherit = 'res.partner'

    @api.constrains('vat', 'l10n_latam_identification_type_id')
    def check_vat(self):
        """ Extention of the validation method to cover DPI/CUI and NIT. """
        l10n_gt_partners = self.filtered(lambda p: p.country_code == 'GT')
        l10n_gt_partners.l10n_gt_identification_validation()
        return super(ResPartner, self - l10n_gt_partners).check_vat()

    def l10n_gt_identification_validation(self):
        for record in self.filtered('vat'):
            record.ensure_one()
            if record.l10n_latam_identification_type_id == self.env.ref('l10n_gt.it_cui'):
                cui_sum = sum(int(a) * b for a, b in zip(record.vat[:8], range(2, 10)))
                cui_res = '0123456789K'[(cui_sum % 11)]
                if record.vat[8] != cui_res:
                    raise ValidationError(_("Incorrect verification digit for the CUI identification type."))
            elif record.l10n_latam_identification_type_id == self.env.ref('l10n_gt.it_nit'):
                stdnum.gt.nit.validate(record.vat)
