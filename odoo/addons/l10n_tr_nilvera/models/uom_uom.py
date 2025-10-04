from odoo import models

UOM_TO_UNECE_CODE = {
    'l10n_tr_nilvera.product_uom_pk': 'PK',
    'l10n_tr_nilvera.product_uom_pf': 'PF',
    'l10n_tr_nilvera.product_uom_cr': 'CR',
    'l10n_tr_nilvera.product_uom_standard_cubic_meter': 'SM3',
    'l10n_tr_nilvera.product_uom_sa': 'SA',
    'l10n_tr_nilvera.product_uom_cmq': 'CMQ',
    'l10n_tr_nilvera.product_uom_mlt': 'MLT',
    'l10n_tr_nilvera.product_uom_mmq': 'MMQ',
    'l10n_tr_nilvera.product_uom_cmk': 'CMK',
    'l10n_tr_nilvera.product_uom_bg': 'BG',
    'l10n_tr_nilvera.product_uom_bx': 'BX',
    'l10n_tr_nilvera.product_uom_pr': 'PR',
    'l10n_tr_nilvera.product_uom_mgm': 'MGM',
    'l10n_tr_nilvera.product_uom_mon': 'MON',
    'l10n_tr_nilvera.product_uom_gt': 'GT',
    'l10n_tr_nilvera.product_uom_ann': 'ANN',
    'l10n_tr_nilvera.product_uom_d61': 'D61',
    'l10n_tr_nilvera.product_uom_d62': 'D62',
    'l10n_tr_nilvera.product_uom_pa': 'PA',
    'l10n_tr_nilvera.product_uom_mwh': 'MWH',
    'l10n_tr_nilvera.product_uom_kwh': 'KWH',
    'l10n_tr_nilvera.product_uom_kwt': 'KWT',
    'l10n_tr_nilvera.product_uom_set': 'SET',
}


class Uom(models.Model):
    _inherit = 'uom.uom'

    def _get_unece_code(self):
        """ This depends on the mapping from https://developer.nilvera.com/en/code-lists#birim-kodlari """
        unece_code = super()._get_unece_code()
        if unece_code == 'C62':
            xml_id = self.get_external_id()
            if xml_id and self.id in xml_id:
                return UOM_TO_UNECE_CODE.get(xml_id[self.id], 'C62')
        return unece_code
