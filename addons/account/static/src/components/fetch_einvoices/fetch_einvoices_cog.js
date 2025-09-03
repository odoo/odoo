import { Component } from "@odoo/owl";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { ACTIONS_GROUP_NUMBER } from "@web/search/action_menus/action_menus";

const cogMenuRegistry = registry.category("cogMenu");

export class FetchEInvoices extends Component {
    static template = "account.FetchEInvoices";
    static props = {};
    static components = { DropdownItem };

    setup() {
        super.setup();
        this.action = useService("action");
    }

    get buttonAction() {
        return this.env.searchModel.globalContext.show_fetch_in_einvoices_button
            ? "button_fetch_in_einvoices"
            : "button_refresh_out_einvoices_status";
    }

    get buttonLabel() {
        return this.env.searchModel.globalContext.show_fetch_in_einvoices_button
            ? _t("Fetch e-Invoices")
            : _t("Refresh e-Invoices Status");
    }

    fetchEInvoices() {
        const journalId = this.env.searchModel.globalContext.default_journal_id;
        if (!journalId) {
            return;
        }

        this.action.doActionButton({
            type: "object",
            resId: journalId,
            name: this.buttonAction,
            resModel: "account.journal",
            onClose: () => window.location.reload(),
        });
    }
}

export const fetchEInvoicesActionMenu = {
    Component: FetchEInvoices,
    groupNumber: ACTIONS_GROUP_NUMBER,
    isDisplayed: ({ config, searchModel }) =>
        searchModel.resModel === "account.move" &&
        (searchModel.globalContext.default_journal_id || false) &&
        (searchModel.globalContext.show_fetch_in_einvoices_button ||
            searchModel.globalContext.show_refresh_out_einvoices_status_button ||
            false),
};

cogMenuRegistry.add("account-fetch-e-invoices", fetchEInvoicesActionMenu, { sequence: 11 });
