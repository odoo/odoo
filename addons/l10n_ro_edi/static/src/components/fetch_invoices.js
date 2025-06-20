import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { useService } from "@web/core/utils/hooks";
import { user } from "@web/core/user";

export class FetchInvoicesCogMenu extends Component {
    static template = "l10n_ro_edi.FetchInvoices";
    static props = {};
    static components = { DropdownItem };

    setup() {
        this.action = useService("action");
        this.orm = useService("orm");
    }

    async fetchInvoices() {
        const { context } = this.env.searchModel;
        return this.action.doActionButton({
            type: "object",
            resModel: "account.move",
            name: "action_l10n_ro_edi_fetch_invoices",
            context: context,
        });
    }
}

export const CogMenuItem = {
    Component: FetchInvoicesCogMenu,
    groupNumber: 20,
    isDisplayed: async ({ config, searchModel, services }) => {
        const orm = services.orm;
        const data = await orm.searchRead("res.company", [["id", "=", user.activeCompany.id]], ["country_code"]);
        const countryCode = data[0]?.country_code;

        return (
            countryCode === "RO" &&
            searchModel.resModel === "account.move" &&
            ["kanban", "list"].includes(config.viewType) &&
            config.actionType === "ir.actions.act_window"
        );
    },
};

registry.category("cogMenu").add("l10n_ro_edi-fetch-invoices", CogMenuItem, { sequence: 10 });
