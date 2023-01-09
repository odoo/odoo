/** @odoo-module **/

import ListController from 'web.ListController';
import ListRenderer from 'web.ListRenderer';
import ListView from 'web.ListView';
import viewRegistry from 'web.view_registry';
import ProjectRightSidePanel from '@project/js/right_panel/project_right_panel';
import {
    RightPanelControllerMixin,
    RightPanelRendererMixin,
    RightPanelViewMixin,
} from '@project/js/right_panel/project_right_panel_mixin';

const ProjectUpdateListRenderer = ListRenderer.extend(RightPanelRendererMixin);

const ProjectUpdateListController = ListController.extend(RightPanelControllerMixin);

export const ProjectUpdateListView = ListView.extend(RightPanelViewMixin).extend({
    config: Object.assign({}, ListView.prototype.config, {
        Controller: ProjectUpdateListController,
        Renderer: ProjectUpdateListRenderer,
        RightSidePanel: ProjectRightSidePanel,
    }),
});

viewRegistry.add('project_update_list', ProjectUpdateListView);
