import { Component } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { useService } from "@web/core/utils/hooks";


export class WOStateDropdown extends Component {
    static template = "mrp.WOStateDropdown";
    static components = {
        Dropdown,
        DropdownItem,
    };
    static props = { ...standardFieldProps };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.colorIcons = {
            "blocked": ["warning", "fa-exclamation-circle"],
            "ready": ["300", "fa-circle"],
            "progress": ["info", "fa-play-circle"],
            "cancel": ["danger", "fa-times-circle"],
            "done": ["success", "fa-check-circle"],
        };
    }

    async reload(){
        await this.env.model.root.load();
        this.env.model.notify();
    }

    statusColor(state) {
        return this.colorIcons[state] ? this.colorIcons[state][0] : "";
    }

    statusIcon(state) {
        return this.colorIcons[state] ? this.colorIcons[state][1] : "";
    }

    stateName(state) {
        const stateName = this.props.record._config.fields.state.selection.find((el) => el[0] == state);
        return stateName ? stateName[1] : "";
    }

    async setState(state) {
        let selectedWorkorders = this.props.record.model.root.selection;
        if (!selectedWorkorders || selectedWorkorders.length == 0) {
            selectedWorkorders = [this.props.record];
        }
        let ids = selectedWorkorders.filter((wo) => !([state, 'done'].includes(wo.data.state) || wo.data.production_state == 'done')).map((wo) => wo.resId)
        let res = false;
        if (ids && ids.length > 0) {
            res = await this.callOrm("set_state", [state], ids);
        }
        console.log(res);
        this.handleWizard(res);
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
            return await this.orm.call("mrp.workorder", functionName, [ids, ...args]);
        } else {
            return await this.orm.call("mrp.workorder", functionName, [ids]);
        }
    }

    handleWizard(res){
        if (res && res.binding_type == "action") { // && res.res_model === "mrp.workorder.incomplete.qty"
            return this.action.doAction(res, { onClose: this.reload.bind(this) });
        }
        else{
            this.reload();
        }
    }
}

export const woStateDropdown = {
    component: WOStateDropdown,
    supportedTypes: ["selection"],
};

registry.category("fields").add("wo_state_dropdown", woStateDropdown);
