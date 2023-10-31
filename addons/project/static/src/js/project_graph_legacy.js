/** @odoo-module **/

import GraphView from 'web.GraphView';
import { ProjectControlPanel } from '@project/js/project_control_panel';
import viewRegistry from 'web.view_registry';

export const ProjectGraphView = GraphView.extend({
  config: Object.assign({}, GraphView.prototype.config, {
    ControlPanel: ProjectControlPanel,
  }),
});

viewRegistry.add('project_graph', ProjectGraphView);
