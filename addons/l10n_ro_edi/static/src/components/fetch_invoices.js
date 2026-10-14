import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { useService } from "@web/core/utils/hooks";
import { user } from "@web/core/user";


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
    isDisplayed: async ({ config, searchModel }) => {
        if (
            searchModel.resModel === "account.move" &&
            ["kanban", "list"].includes(config.viewType) &&
            config.actionType === "ir.actions.act_window"
<<<<<<< 6159da4b6fbf3280f09881dc92f2e532d435e996
        ) {
            const data = await searchModel.orm
                .cache({ type: "disk" })
                .read("res.company", [user.activeCompany.id], ["country_code"]);
            return data[0]?.country_code === 'RO';
        }
||||||| f1724fcca60f0935a522d28c179c643483991d03
        );
=======
        ) {
            const data = await searchModel.orm.read("res.company", [user.activeCompany.id], ["country_code"]);
            return data[0]?.country_code === 'RO';
        }
        return false;
>>>>>>> 9fad8baf4744cc72d81c3322c79624bd6498997f
    },
};

registry.category("cogMenu").add("l10n_ro_edi-fetch-invoices", CogMenuItem, { sequence: 10 });
