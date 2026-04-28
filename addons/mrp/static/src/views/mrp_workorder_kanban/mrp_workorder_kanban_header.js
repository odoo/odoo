/** @odoo-module **/

import { KanbanHeader } from "@web/views/kanban/kanban_header";
import { SelectCreateDialog } from "@web/views/view_dialogs/select_create_dialog";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

export class MrpWorkorderKanbanHeader extends KanbanHeader {
    setup() {
        super.setup();
        this.dialog = useService("dialog");
    }

    canQuickCreate() {
        return true;
    }

    async quickCreate() {
        const { groupByField, value } = this.group;
        this.dialog.add(SelectCreateDialog, {
            resModel: this.props.list.resModel,
            noCreate: true,
            multiSelect: true,
            context: {
                search_default_workcenter_id: value,
                search_default_ready: true,
                search_default_blocked: true,
                search_default_filter_to_plan: true,
                search_default_progress: true,
                search_view_ref: "mrp.view_mrp_production_workorder_form_view_filter",
                list_view_ref: "mrp.mrp_production_workorder_to_plan_list",
            },
            title: _t("Add Work Orders to planning"),
            onSelected: async (resIds) => {
                await this.orm.write(this.props.list.resModel, resIds, {
                    [groupByField.name]: value,
                });
                await this.orm.call(this.props.list.resModel, "action_replan", [resIds])
                await this.props.list.model.load();
            },
        });
    }
}
