import { ListController } from "@web/views/list/list_controller";
import { onWillStart } from "@odoo/owl";
import { user } from "@web/core/user";

import { ProjectTemplateDropdown } from "../components/project_template_dropdown";

export class ProjectListController extends ListController {
    static template = "project.ProjectListView";
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
        const embeddedSettings = await this.orm.call(
            "res.users.settings",
            "get_embedded_actions_settings",
            [user.settings.id],
            { res_model: this.modelParams.config.resModel, res_ids: duplicatedRecords }
        );
        user.updateUserSettings("embedded_actions_config_ids", embeddedSettings);
    }
}
