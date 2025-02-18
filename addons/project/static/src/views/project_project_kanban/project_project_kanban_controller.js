import { KanbanController } from "@web/views/kanban/kanban_controller";
import { onWillStart } from "@odoo/owl";
import { user } from "@web/core/user";

export class ProjectKanbanController extends KanbanController {
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
};
