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

    get isUserProjectManager() {
        if (this.isProjectManager) {
            return true;
        }
        const records = this.props.list?.records || [];
        return (
            /** Truthy even with no records: allows project managers to edit stages even with no task created yet.
             * This displays the edit button to any generic project_user with no edition privileges
             * but project_task_type.write() ensures they see an error when they try to save their modifications.
             */
            records.every((record) => record.data.is_user_project_manager)
        );
    }

    async deleteGroup() {
        return this.props.deleteGroup(this.group);
    }

    canEditGroup() {
        /* Make the "Edit" button visible even when no task is visible due to filters or because the project is brand new.*/
        if (this.props.list.isGroupedByStage && this.isUserProjectManager) {
            return Boolean(this.props.group.groupByField.relation);
        }
        return super.canEditGroup();
    }

    canDeleteGroup() {
        return (
            super.canDeleteGroup() && (!this.props.list.isGroupedByStage || this.isProjectManager)
        );
    }
}
