import { Component, useState } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { registry } from "@web/core/registry";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";
import { useService } from "@web/core/utils/hooks";


export class MOListViewDropdown extends Component {
    static template = "mrp.MOViewListDropdown";
    static components = {
        Dropdown,
        DropdownItem,
    };
    static props = { ...standardWidgetProps };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.workorderState = useState({
            state: this.props.record.data.state,
        });
        this.colorIcons = {
            "blocked": "bg-warning",
            "ready": "bg-muted",
            "progress": "bg-info",
            "cancel": "bg-danger",
            "done": "bg-success",
        };
    }

    async reload(){
        await this.env.model.root.load();
        this.env.model.notify();
    }

    get statusColor() {
        const state = this.workorderState.state;
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
}

export const moListViewDropdown = {
    listViewWidth: 20,
    component: MOListViewDropdown,
};

registry.category("view_widgets").add("mo_view_list_dropdown", moListViewDropdown);
