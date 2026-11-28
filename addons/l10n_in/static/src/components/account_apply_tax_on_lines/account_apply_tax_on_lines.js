import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { AccountApplyTaxOnLines } from "@account/components/account_apply_tax_on_lines/account_apply_tax_on_lines";

patch(AccountApplyTaxOnLines.prototype, {
    get isIndianCompany() {
        return this.props.record.data.country_code === "IN";
    },

    get availableCountryCodes() {
        return [...super.availableCountryCodes, "IN"];
    },

    get isVisible() {
        // TCS taxes are archived as long as the TCS feature is disabled on the company.
        return super.isVisible && this.props.record.data.l10n_in_tcs_feature_enabled;
    },

    get buttonLabel() {
        return this.isIndianCompany ? _t("Apply TCS") : super.buttonLabel;
    },

    get buttonTooltip() {
        return this.isIndianCompany
            ? _t("Apply the selected TCS tax to all the invoice lines")
            : super.buttonTooltip;
    },

    get taxDomain() {
        if (!this.isIndianCompany) {
            return super.taxDomain;
        }
        // TCS taxes are sale taxes but are also proposed on bills, hence no type_tax_use filter.
        return [
            ["l10n_in_tax_type", "=", "tcs"],
            ["company_id", "parent_of", this.props.record.data.company_id.id],
        ];
    },
});
