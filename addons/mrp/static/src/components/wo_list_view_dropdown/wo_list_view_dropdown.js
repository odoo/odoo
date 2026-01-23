import { useState } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { useService } from "@web/core/utils/hooks";
import { BadgeField, badgeField } from "@web/views/fields/badge/badge_field";

export class MOListViewDropdown extends BadgeField {
    static template = "mrp.MOViewListDropdown";
    static components = {
        Dropdown,
        DropdownItem,
    };

    static props = {
        ...standardFieldProps,
        display: { type: String, validate: (val) => ["bubble", "badge"].includes(val)} ,
    };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.workorderState = useState({
            state: this.props.record.data.state,
        });
        this.colorIcons = {
            "blocked": "text-bg-warning",
            "ready": "text-bg-secondary",
            "progress": "text-bg-info",
            "cancel": "text-bg-danger",
            "done": "text-bg-success",
        };
    }

    async reload(){
        await this.env.model.root.load();
        this.env.model.notify();
    }

    get statusColor() {
        const state = this.props.record.data.state;
        return this.colorIcons[state] || "";
    }

    async setState(state) {
        let selectedWorkorders = this.props.record.model.root.selection;
        if (!selectedWorkorders || selectedWorkorders.length == 0) {
            selectedWorkorders = [this.props.record];
        }
        let ids = selectedWorkorders.filter((wo) => !([state, 'done'].includes(wo.data.state) || wo.data.production_state == 'done')).map((wo) => wo.resId)  
        if (ids && ids.length > 0) {
            await this.callOrm("set_state", [state], ids);
        }
    }


    async callOrm(functionName, args, ids = undefined) {
        if (!ids){
            ids = this.props.record.model.root.selection?.map((element) => element.evalContext.id);
        }
        // if no records selected, take the current clicked one
        if (!ids || ids.length == 0) {
            ids = [this.props.record.resId];
        }
        if (args !== undefined) {
            await this.orm.call("mrp.workorder", functionName, [ids, ...args]);
        } else {
            await this.orm.call("mrp.workorder", functionName, [ids]);
        }
        await this.reload();
    }
};

registry.category("fields").add("mo_view_list_dropdown", {
    ...badgeField,
    supportedOptions: [
        {
            name: "display",
            type: "String"
        }
    ],
    extractProps: ({ options }) => ({
        display: options.display,
    }),
    component: MOListViewDropdown,
});
