/** @odoo-module **/

import KanbanController from 'web.KanbanController';
import KanbanRenderer from 'web.KanbanRenderer';
import KanbanView from 'web.KanbanView';
import viewRegistry from 'web.view_registry';
import ProjectRightSidePanel from '@project/js/right_panel/project_right_panel';
import {
    RightPanelControllerMixin,
    RightPanelRendererMixin,
    RightPanelViewMixin,
} from '@project/js/right_panel/project_right_panel_mixin';

const ProjectUpdateKanbanRenderer = KanbanRenderer.extend(RightPanelRendererMixin);

const ProjectUpdateKanbanController = KanbanController.extend(RightPanelControllerMixin);

export const ProjectUpdateKanbanView = KanbanView.extend(RightPanelViewMixin).extend({
    config: Object.assign({}, KanbanView.prototype.config, {
        Controller: ProjectUpdateKanbanController,
        Renderer: ProjectUpdateKanbanRenderer,
        RightSidePanel: ProjectRightSidePanel,
    }),
});

viewRegistry.add('project_update_kanban', ProjectUpdateKanbanView);
