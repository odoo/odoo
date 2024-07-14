/** @odoo-module */

import { PartnerDetailsEdit } from "@point_of_sale/app/screens/partner_list/partner_editor/partner_editor";
import { patch } from "@web/core/utils/patch";

patch(PartnerDetailsEdit.prototype, {
    setup() {
        super.setup(...arguments);
        this.changes.l10n_mx_edi_fiscal_regime = this.getPartnerMxFiscalRegime();
        this.changes.l10n_mx_edi_no_tax_breakdown = this.props.partner.l10n_mx_edi_no_tax_breakdown;
    },
    isMexicoSelected() {
        return (
            this.pos.countries.find((country) => country.code === "MX").id ===
            parseInt(this.changes.country_id)
        );
    },
    getPartnerMxFiscalRegime() {
        return (
            this.props.partner.l10n_mx_edi_fiscal_regime &&
            this.pos.l10n_mx_edi_fiscal_regime.find(
                (regime) => regime.value === this.props.partner.l10n_mx_edi_fiscal_regime
            )?.value
        );
    },
});
