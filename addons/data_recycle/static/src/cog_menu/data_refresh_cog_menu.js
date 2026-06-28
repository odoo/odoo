import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { registry } from "@web/core/registry";
import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

const cogMenuRegistry = registry.category("cogMenu");

export class DataRefreshCogMenu extends Component {
    static template = "data_recycle.DataRefreshCogMenu";
    static components = { DropdownItem };
    static props = {};

    setup() {
        this.action = useService("action");
    }

    _getDomainValue(fieldName) {
        // The searchpanel adds the selected rule to the domain as
        // ['fieldName', '=', <id>]. We extract that id from the
        // current domain and pass it in the action context so that,
        // after refresh, the same rule remains selected in seachpanel.
        const domain = this.env.searchModel.domain;
        return domain.find((d) => Array.isArray(d) && d[0] === fieldName && d[1] === "=")?.[2];
    }

    async refreshData() {
        const ruleId = this._getDomainValue("recycle_model_id");;
        return await this.action.doActionButton({
            type: "object",
            resModel: "data_recycle.model",
            name: "refresh_recycle_records",
            context: {
                recycle_model_id: ruleId,
            }
        });
    }
}

export const DataRefreshCogMenuItem = {
    Component: DataRefreshCogMenu,
    isDisplayed: ({ searchModel }) => {
        return searchModel.resModel === "data_recycle.record";
    },
    groupNumber: 50,
};

cogMenuRegistry.add("data_refresh_menu", DataRefreshCogMenuItem, { sequence: 10 });
