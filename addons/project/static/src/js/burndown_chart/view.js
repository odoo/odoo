/** @odoo-module alias=project.BurndownChartView **/
import GraphView from 'web.GraphView';
import viewRegistry from 'web.view_registry';
import BurndownChartController from './controller';
import { BurndownChartRenderer } from './renderer';

export const BurndownChartView = GraphView.extend({
    config: Object.assign({}, GraphView.prototype.config, {
        Controller: BurndownChartController,
        Renderer: BurndownChartRenderer,
    }),
});

viewRegistry.add('burndown_chart', BurndownChartView);
