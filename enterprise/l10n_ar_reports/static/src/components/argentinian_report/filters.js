import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { AccountReportFilters } from "@account_reports/components/account_report/filters/filters";

patch(AccountReportFilters.prototype, {
    get selectedTaxType() {
        const availableTypes = Object.keys(this.controller.options.ar_vat_book_tax_types_available);
        const selectedTypes = Object.values(
            this.controller.options.ar_vat_book_tax_types_available,
        ).filter((type) => type.selected);

        if (selectedTypes.length === availableTypes.length || selectedTypes.length === 0) {
            return _t("All");
        }

        return selectedTypes.map((type) => type.name).join(", ");
    },

    selectArVatBookTaxType(taxType) {
        const newArVatBookTaxTypes = Object.assign(
            {},
            this.controller.options.ar_vat_book_tax_types_available,
        );
        newArVatBookTaxTypes[taxType]["selected"] = !newArVatBookTaxTypes[taxType]["selected"];
        this.filterClicked({ optionKey: "ar_vat_book_tax_types_available", optionValue: newArVatBookTaxTypes, reload: true});
    },
});
