/** @odoo-module native */
import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { user } from "@web/core/user";
import { useService } from "@web/core/utils/hooks";
import { COG_GROUP, isActWindowView } from "@web/search/cog_menu/cog_menu_group";
import { CogMenuItem } from "@web/search/cog_menu/cog_menu_item";

export class FetchInvoicesCogMenu extends Component {
    static template = "l10n_ro_edi.FetchInvoices";
    static props = {};
    static components = { CogMenuItem };

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

export const fetchInvoicesCogMenuItem = {
    Component: FetchInvoicesCogMenu,
    groupNumber: COG_GROUP.APP,
    isDisplayed: async (env) => {
        if (
            env.searchModel.resModel !== "account.move" ||
            !isActWindowView(env, ["kanban", "list"])
        ) {
            return false;
        }
        const data = await env.searchModel.orm.read(
            "res.company",
            [user.activeCompany.id],
            ["country_code"],
        );
        return data[0]?.country_code === "RO";
    },
};

registry
    .category("cogMenu")
    .add("l10n_ro_edi-fetch-invoices", fetchInvoicesCogMenuItem, { sequence: 10 });
