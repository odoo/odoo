import { KanbanController } from "@web/views/kanban/kanban_controller";
import { onWillStart } from "@odoo/owl";
import { user } from "@web/core/user";

import { ProjectTemplateDropdown } from "../components/project_template_dropdown";

export class ProjectKanbanController extends KanbanController {
    static template = "project.ProjectKanbanView";
    static components = {
        ...KanbanController.components,
        ProjectTemplateDropdown,
    };

    setup() {
        super.setup();
        onWillStart(async () => {
            this.isProjectManager = await user.hasGroup('project.group_project_manager');
        });
    }

    getStaticActionMenuItems() {
        const actionMenuItems = super.getStaticActionMenuItems(...arguments);
        if (!this.isProjectManager) {
            ['duplicate', 'archive', 'unarchive'].forEach(item => delete actionMenuItems[item]);
        }
        return actionMenuItems;
    }

    /**
     * @override
     */
    async onDuplicatedMulti(originalRecords, duplicatedRecords) {
        await super.onDuplicatedMulti(...arguments);
        const embeddedSettings = await this.model.orm.call(
            "res.users.settings",
            "get_embedded_actions_settings",
            [user.settings.id],
            { res_model: this.modelParams.config.resModel, res_ids: duplicatedRecords }
        );
        user.updateUserSettings("embedded_actions_config_ids", embeddedSettings);
    }
}
