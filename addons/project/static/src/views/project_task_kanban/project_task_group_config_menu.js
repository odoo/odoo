import { onWillStart } from "@odoo/owl";
import { user } from "@web/core/user";
import { useService } from "@web/core/utils/hooks";
import { GroupConfigMenu } from "@web/views/view_components/group_config_menu";

export class ProjectTaskGroupConfigMenu extends GroupConfigMenu {
    setup() {
        super.setup();
        this.action = useService("action");

        this.isProjectManager = false;
        onWillStart(async () => {
            if (this.props.list.isGroupedByStage) {
                this.isProjectManager = await user.hasGroup("project.group_project_manager");
            }
        });
    }

    async deleteGroup() {
        if (this.group.groupByField.name === "stage_id") {
            const action = await this.group.model.orm.call(
                this.group.groupByField.relation,
                "unlink_wizard",
                [this.group.value],
                { context: this.group.context }
            );
            this.action.doAction(action);
            return;
        }
        super.deleteGroup();
    }

    canEditGroup() {
        return super.canEditGroup() && (!this.props.list.isGroupedByStage || this.isProjectManager);
    }

    canDeleteGroup() {
        return (
            super.canDeleteGroup() && (!this.props.list.isGroupedByStage || this.isProjectManager)
        );
    }
}
