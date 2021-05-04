/** @odoo-module **/

import { _t } from 'web.core';
import GraphController from 'web.GraphController';
import GraphView from 'web.GraphView';
import PivotController from 'web.PivotController';
import PivotView from 'web.PivotView';
import viewRegistry from 'web.view_registry';

const ProjectPivotController = PivotController.extend({
    /**
     * @override
     */
    init: function () {
        this._super.apply(this, arguments);
        const measures = JSON.parse(JSON.stringify(this.measures));
        if ('res_id' in measures) {
            measures.res_id.string = _t('Task');
        }
        if ('parent_res_id' in measures) {
            measures.parent_res_id.string = _t('Project');
        }
        if ('rating' in measures) {
            measures.rating.string = _t('Rating Value (/5)');
        }
        this.measures = measures;
    },
});

const ProjectPivotView = PivotView.extend({
    config: Object.assign({}, PivotView.prototype.config, {
        Controller: ProjectPivotController,
    }),
});

viewRegistry.add('project_rating_pivot', ProjectPivotView);

const ProjectGraphController = GraphController.extend({
    /**
     * @override
     */
    init: function () {
        this._super.apply(this, arguments);
        _.each(this.measures, measure => {
            if (measure.fieldName === 'res_id') {
                measure.description = _t('Task');
            } else if (measure.fieldName === 'parent_res_id') {
                measure.description = _t('Project');
            } else if (measure.fieldName === 'rating') {
                measure.description = _t('Rating Value (/5)');
            }
        });
    },
});

const ProjectGraphView = GraphView.extend({
    config: Object.assign({}, GraphView.prototype.config, {
        Controller: ProjectGraphController,
    }),
});

viewRegistry.add('project_rating_graph', ProjectGraphView);
