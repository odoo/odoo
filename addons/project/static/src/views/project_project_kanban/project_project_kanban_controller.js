import { KanbanController } from "@web/views/kanban/kanban_controller";
import { RottingKanbanController } from "@mail/js/rotting_mixin/rotting_kanban_controller";
import { onWillStart } from "@odoo/owl";
import { user } from "@web/core/user";

import { ProjectTemplateDropdown } from "../components/project_template_dropdown";

export const ProjectKanbanControllerMixin = (ViewController) =>
    class extends ViewController {
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

export class ProjectKanbanController extends ProjectKanbanControllerMixin(KanbanController) {
    static components = {
        ...KanbanController.components,
        ProjectTemplateDropdown,
    };
};

export class ProjectKanbanGroupStageController extends ProjectKanbanControllerMixin(RottingKanbanController) {
    static components = {
        ...RottingKanbanController.components,
        ProjectTemplateDropdown,
    };
};
