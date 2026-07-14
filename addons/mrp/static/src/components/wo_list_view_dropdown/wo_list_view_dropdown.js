import { Component, useState } from "@odoo/owl";
import { downloadReport } from "@web/webclient/actions/reports/utils";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";
import { _t } from "@web/core/l10n/translation";
import { user } from "@web/core/user";
import { useService } from "@web/core/utils/hooks";

const workcenterStatusBlocked = "blocked";

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
            "done": "o_status_success",
            [workcenterStatusBlocked]: "o_status_danger",
        };
    }

    async reload(){
        await this.env.model.root.load();
        this.env.model.notify();
    }

    get statusColor() {
        const state = this.isBlocked ? workcenterStatusBlocked : this.workorderState.state;
        return this.colorIcons[state] || "";
    }

    get isBlocked() {
        return this.props.record.data.working_state == workcenterStatusBlocked;
    }

    get blockTitle(){
        if (this.isBlocked) {
            return _t("Unblock");
        }
        return _t("Block");
    }

    async toggleBlock() {
        if (this.isBlocked) {
            await this.callOrm("button_unblock");
            return;
        }
        const options = {
            additionalContext: { default_workcenter_id: this.props.record.data.workcenter_id[0] },
            onClose: async () => {
                await this.reload();
            },
        };
        this.action.doAction("mrp.act_mrp_block_workcenter_wo", options);
    }

    async markAsDone() {
        await this.callOrm("action_mark_as_done");
    }

    async printWO() {
        await downloadReport(
            rpc,
            {
                ...{ report_name: "mrp.report_mrp_workorder", report_type: "qweb-pdf" },
                context: { active_ids: [this.props.record.resId] },
            },
            "pdf",
            user.context
        );
    }

    async callOrm(functionName){
        let ids = this.props.record.model.root.selection?.map((element) => element.evalContext.id);
        // if no records selected, take the current clicked one
        if (!ids || ids.length == 0) {
            ids = [this.props.record.resId];
        }
        await this.orm.call("mrp.workorder", functionName, [ids]);
        await this.reload();
    }
}

export const moListViewDropdown = {
    listViewWidth: 20,
    component: MOListViewDropdown,
};

registry.category("view_widgets").add("mo_view_list_dropdown", moListViewDropdown);
