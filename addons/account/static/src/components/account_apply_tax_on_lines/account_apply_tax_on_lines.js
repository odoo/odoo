import { Component, useProps } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { SelectCreateDialog } from "@web/views/view_dialogs/select_create_dialog";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";
import { usePopover } from "@web/core/popover/popover_hook";
import { user } from "@web/core/user";
import { DropdownPopover } from "@web/core/dropdown/_behaviours/dropdown_popover";

export class AccountApplyTaxOnLines extends Component {
    static template = "account.ApplyTaxOnLines";

    props = useProps(standardWidgetProps);

    setup() {
        this.orm = useService("orm");
        this.dialogService = useService("dialog");
        this.actionService = useService("action");
        this.taxPopover = usePopover(DropdownPopover, {
            popoverClass: "o-dropdown--menu dropdown-menu o_cash_rounding_dropdown",
            position: "left-middle",
            role: "menu",
        });
    }

    /**
     * This widget is not needed to be displayed for all countries.
     * Override this to add a country for which this is needed.
     */
    get availableCountryCodes() {
        return [];
    }

    get isVisible() {
        return (
            !this.props.readonly &&
            this.availableCountryCodes.includes(this.props.record.data.country_code)
        );
    }

    get buttonLabel() {
        return _t("Add Tax");
    }

    get buttonTooltip() {
        return _t("Add the selected tax to all the invoice lines");
    }

    /**
     * Domain of the account.tax list opened by the widget.
     * Keep it in sync with `_get_tax_popover_domain()` method on account
     */
    get taxDomain() {
        const { invoice_filter_type_domain, company_id } = this.props.record.data;
        return [
            ["type_tax_use", "=?", invoice_filter_type_domain],
            ["company_id", "parent_of", company_id?.id || user.activeCompany.id],
        ];
    }

    async getTaxPopoverItems() {
        const { total_length, records, applied_tax_id } = await this.orm.call(
            "account.move",
            "get_taxes_to_show",
            [this.props.record.data.id]
        );
        const items = [
            {
                id: "taxes",
                label: _t("Select Tax"),
                class: "o_cash_rounding_dropdown_title",
                onSelected: () => {},
            },
        ];
        items.push(
            ...records.map((tax) => ({
                id: `tax_${tax.id}`,
                label: tax.name,
                class: {
                    o_cash_rounding_dropdown_selected: tax.id === applied_tax_id,
                },
                onSelected: () => this.updateInvoiceLinesOnTaxSelection(tax.id),
            }))
        );
        if (records.length === 0) {
            items.push({
                id: "no_record",
                label: "No records",
                class: "o_m2o_no_result",
                onSelected: () => {},
            })
        } else if (total_length > records.length) {
            items.push({
                id: "search_more",
                label: _t("Search more..."),
                class: "o_cash_rounding_dropdown_action",
                onSelected: () => this.openTaxesListview(),
            });
        }
        return items;
    }

    async openTaxDialog(target) {
        if (this.taxPopover.isOpen) {
            this.taxPopover.close();
            return;
        }
        const items = await this.getTaxPopoverItems();
        this.taxPopover.open(target, { items, slots: {} });
    }

    openTaxesListview() {
        this.dialogService.add(SelectCreateDialog, {
            resModel: "account.tax",
            title: _t("Select Tax"),
            multiSelect: false,
            noCreate: true,
            domain: this.taxDomain,
            onSelected: (resIds) => this.updateInvoiceLinesOnTaxSelection(resIds[0]),
        });
    }

    async updateInvoiceLinesOnTaxSelection(taxId) {
        this.taxPopover.close();
        await this.orm.call("account.move", "update_or_add_tax_on_invoice_lines", [
            this.props.record.data.id,
            taxId,
        ]);
        this.actionService.doAction("soft_reload");
    }
}

export const accountApplyTaxOnLines = {
    component: AccountApplyTaxOnLines,
};

registry.category("view_widgets").add("account_apply_tax_on_lines", accountApplyTaxOnLines);
