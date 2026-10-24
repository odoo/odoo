import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { user } from "@web/core/user";
import { useService } from "@web/core/utils/hooks";
import { TaxTotalsComponent } from "@account/components/tax_totals/tax_totals";
import { SelectCreateDialog } from "@web/views/view_dialogs/select_create_dialog";

patch(TaxTotalsComponent.prototype, {
    setup() {
        super.setup();
        this.action = useService("action");
    },

    async getCashRoundingDropdownItems() {
        const items = await super.getCashRoundingDropdownItems();
        if (this.props.record.data.country_code !== "IN") {
            return items;
        }

        const { total_length, records, applied_tax_id } = await this.orm.call(
            "account.move",
            "get_l10n_in_tcs_taxes",
            [this.props.record.data.id]
        );

        items.push({
            id: "tcs_selection",
            label: _t("TCS Taxes to apply"),
            class: "o_cash_rounding_dropdown_title",
            onSelected: () => {},
        });
        items.push(
            ...records.map((tax) => ({
                id: `tcs_${tax.id}`,
                label: tax.name,
                class: {
                    o_cash_rounding_dropdown_selected: tax.id === applied_tax_id,
                },
                onSelected: () => this.updateInvoiceLinesOnTaxSelection(tax.id),
            }))
        );
        if (total_length > records.length) {
            items.push({
                id: "tcs_search_more",
                label: _t("Search more..."),
                class: "o_cash_rounding_dropdown_action",
                onSelected: () => this.openTcsTaxesListview(),
            });
        }
        return items;
    },

    async updateInvoiceLinesOnTaxSelection(taxId) {
        await this.orm.call("account.move", "l10n_in_update_add_tcs_on_invoice_lines", [
            this.props.record.data.id,
            taxId,
        ]);
        this.action.doAction("soft_reload");
    },

    openTcsTaxesListview() {
        const allowedCompanies = this.props.record.data.company_id.id || user.activeCompany.id;
        this.dialogService.add(SelectCreateDialog, {
            resModel: "account.tax",
            title: _t("Select TCS Tax to Apply"),
            multiSelect: false,
            noCreate: true,
            domain: [["l10n_in_tax_type", "=", "tcs"], ["company_id", "=", allowedCompanies]],
            onSelected: (resIds) => this.updateInvoiceLinesOnTaxSelection(resIds[0]),
        });
    },
});
