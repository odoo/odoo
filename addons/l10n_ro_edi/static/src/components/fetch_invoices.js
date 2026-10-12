import { Component } from "@odoo/owl";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { registry } from "@web/core/registry";
import { user } from "@web/core/user";
import { useService } from "@web/core/utils/hooks";
import { useEnv } from "@web/owl2/utils";


export class FetchInvoicesCogMenu extends Component {
    static template = "l10n_ro_edi.FetchInvoices";
    static components = { DropdownItem };

    setup() {
        this.action = useService("action");
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
    async isDisplayed() {
        const env = useEnv();
        const data = await env.searchModel.orm.read("res.company", [user.activeCompany.id], ["country_code"]);
        return (
            data[0]?.country_code === 'RO' &&
            env.searchModel.resModel === "account.move" &&
            ["kanban", "list"].includes(env.config.viewType) &&
            env.config.actionType === "ir.actions.act_window"
        );
    },
};

registry.category("cogMenu").add("l10n_ro_edi-fetch-invoices", CogMenuItem, { sequence: 10 });
