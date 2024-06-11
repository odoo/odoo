/** @odoo-module */

import { KanbanController } from '@web/views/kanban/kanban_controller';
import { ProjectRightSidePanel } from '../../components/project_right_side_panel/project_right_side_panel';

export class ProjectUpdateKanbanController extends KanbanController {
    get className() {
        return super.className + ' o_controller_with_rightpanel';
    }
}

ProjectUpdateKanbanController.components = {
    ...KanbanController.components,
    ProjectRightSidePanel,
};
ProjectUpdateKanbanController.template = 'project.ProjectUpdateKanbanView';
