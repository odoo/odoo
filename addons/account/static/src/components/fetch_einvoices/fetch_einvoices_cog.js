/** @odoo-module native */
import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/translation";
import { useService } from "@web/core/utils/hooks";
import { COG_GROUP, isActWindowView } from "@web/search/cog_menu/cog_menu_group";
import { CogMenuItem } from "@web/search/cog_menu/cog_menu_item";

const cogMenuRegistry = registry.category("cogMenu");

export class FetchEInvoices extends Component {
    static template = "account.FetchEInvoices";
    static props = {};
    static components = { CogMenuItem };

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
    groupNumber: COG_GROUP.APP,
    isDisplayed: (env) => {
        const { globalContext, resModel } = env.searchModel;
        return (
            resModel === "account.move" &&
            isActWindowView(env, ["kanban", "list"]) &&
            Boolean(globalContext.default_journal_id) &&
            Boolean(
                globalContext.show_fetch_in_einvoices_button ||
                globalContext.show_refresh_out_einvoices_status_button,
            )
        );
    },
};

cogMenuRegistry.add("account-fetch-e-invoices", fetchEInvoicesActionMenu, {
    sequence: 11,
});
