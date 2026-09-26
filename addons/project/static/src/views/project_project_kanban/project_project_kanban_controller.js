import { FormViewDialog } from "@web/views/view_dialogs/form_view_dialog";
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

        async createRecord() {
            const { onCreate } = this.props.archInfo;
            if (!onCreate || onCreate === "quick_create") { return super.createRecord(...arguments) }

            const action = await this.actionService.loadAction(onCreate);
            if (!action || action.type !== "ir.actions.act_window") { return super.createRecord(...arguments) }

            await this.dialog.add(FormViewDialog, {
                title: action.name,
                resModel: action.res_model,
                viewId: action.views?.find(([, type]) => type === "form")?.[0],
                context: { ...this.model.root.context, ...action.context },
            });
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
