import { ListController } from "@web/views/list/list_controller";
import { onWillStart } from "@odoo/owl";
import { user } from "@web/core/user";

import { ProjectTemplateDropdown } from "../components/project_template_dropdown";

export class ProjectListController extends ListController {
    static components = {
        ...ListController.components,
        ProjectTemplateDropdown,
    };

    setup() {
        super.setup();
        onWillStart(async () => {
            this.isProjectManager = await user.hasGroup('project.group_project_manager');
        });
    }

    get isManagerForSelection() {
        if (this.isProjectManager) {
            return true;
        }
        const selectedRecords = this.model.root.selection;
        return (
            selectedRecords.length > 0 &&
            selectedRecords.every((record) => record.data.is_user_project_manager)
        );
    }

    getStaticActionMenuItems() {
        const actionMenuItems = super.getStaticActionMenuItems(...arguments);
        if (!this.isProjectManager) {
            delete actionMenuItems.duplicate;
            if (actionMenuItems.archive.isAvailable) {
                actionMenuItems.archive.isAvailable = () => this.isManagerForSelection;
            }
            if (actionMenuItems.unarchive.isAvailable) {
                actionMenuItems.unarchive.isAvailable = () => this.isManagerForSelection;
            }
        }
        return actionMenuItems;
    }
};
