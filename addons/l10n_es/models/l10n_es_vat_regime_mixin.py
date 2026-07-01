from odoo import api, fields, models


class L10nESVatRegimeMixin(models.AbstractModel):
    _name = 'l10n.es.vat.regime.mixin'
    _description = "Mixin to manage the VAT Regime Code in Spanish localization"

    _REGIME_CODES_BY_USE = {
        'sale': [
            '01', '03', '04', '05', '06', '07', '08',
            '02_sale', '09_sale', '12_sale', '13_sale',
            '10', '11', '14', '15', '17', '18', '19', '20',
        ],
        'purchase': [
            '01', '03', '04', '05', '06', '07', '08',
            '02_purchase', '09_purchase', '12_purchase', '13_purchase',
            '16',
        ],
    }

    l10n_es_available_vat_regime_code_ids = fields.Char(
        string="Available VAT Regime Codes",
        compute="_compute_l10n_es_vat_regime_available",
        help="Technical field to enable a dynamic selection of the field \"VAT Regime Code\"",
    )
    l10n_es_vat_regime_code_id = fields.Selection(
        string="VAT Regime Code",
        selection="_l10n_es_vat_regime_code_selection",
        compute="_compute_l10n_es_vat_regime_codes",
        readonly=False,
        store=True,
    )
    l10n_es_vat_regime_code_additional = fields.Selection(
        string="VAT Regime Code (Additional)",
        selection="_l10n_es_vat_regime_code_selection",
        compute="_compute_l10n_es_vat_regime_codes",
        readonly=False,
        store=True,
    )

    @api.model
    def _l10n_es_vat_regime_code_selection(self):
        return sorted([
            # Shared
            ('01', "01 - Operación de régimen general"),
            ('03', "03 - Bienes usados, arte, antigüedades y colección"),
            ('04', "04 - Oro de inversión"),
            ('05', "05 - Agencias de viajes"),
            ('06', "06 - Grupo de entidades en IVA (Nivel Avanzado)"),
            ('07', "07 - Criterio de caja"),
            ('08', "08 - IPSI / IGIC"),
            # Same number, different meaning
            ('02_sale', "02 - Exportación"),
            ('02_purchase', "02 - Compensaciones REAGYP en adquisiciones"),
            ('09_sale', "09 - Agencias mediadoras (D.A.4ª RD1619/2012)"),
            ('09_purchase', "09 - Adquisiciones intracomunitarias"),
            ('12_sale', "12 - Arrendamiento local no sujeto a retención"),
            ('12_purchase', "12 - Arrendamiento local de negocio"),
            ('13_sale', "13 - Arrendamiento local sujeto y no sujeto a retención"),
            ('13_purchase', "13 - Importación sin DUA"),
            # Sales only
            ('10', "10 - Cobros por cuenta de terceros"),
            ('11', "11 - Arrendamiento sujeto a retención"),
            ('14', "14 - IVA pendiente — certificaciones de obra (AAPP)"),
            ('15', "15 - IVA pendiente — tracto sucesivo"),
            ('17', "17 - OSS e IOSS"),
            ('18', "18 - Recargo de equivalencia"),
            ('19', "19 - REAGYP"),
            ('20', "20 - Régimen simplificado"),
            # Purchases only
            ('16', "16 - Primer semestre — deducción por cuotas pendientes"),
        ], key=lambda x: x[1])

    def _l10n_es_vat_regime_get_use(self):
        """Override in each model to return 'sale' or 'purchase'."""
        raise NotImplementedError

    @api.depends()
    def _compute_l10n_es_vat_regime_available(self):
        for record in self:
            use = record._l10n_es_vat_regime_get_use()
            valid = record._REGIME_CODES_BY_USE.get(use, [])
            record.l10n_es_available_vat_regime_code_ids = ','.join(valid) if valid else False

    @api.depends()
    def _compute_l10n_es_vat_regime_codes(self):
        for record in self:
            use = record._l10n_es_vat_regime_get_use()
            valid = record._REGIME_CODES_BY_USE.get(use, [])
            if record.l10n_es_vat_regime_code_id not in valid:
                record.l10n_es_vat_regime_code_id = False
            if record.l10n_es_vat_regime_code_additional not in valid:
                record.l10n_es_vat_regime_code_additional = False
