odoo.define('project.project_rating_reporting', function (require) {
'use strict';

const core = require('web.core');
const _t = core._t;

const viewRegistry = require('web.view_registry');

const PivotController = require('web.PivotController');
const PivotView = require('web.PivotView');

const GraphController = require('web.GraphController');
const GraphView = require('web.GraphView');

var ProjectPivotController = PivotController.extend({
    /**
     * @override
     */
    init: function () {
        this._super.apply(this, arguments);
        var measures = JSON.parse(JSON.stringify(this.measures));
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

var ProjectPivotView = PivotView.extend({
    config: _.extend({}, PivotView.prototype.config, {
        Controller: ProjectPivotController,
    }),
});

viewRegistry.add('project_rating_pivot', ProjectPivotView);

var ProjectGraphController = GraphController.extend({
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

var ProjectGraphView = GraphView.extend({
    config: _.extend({}, GraphView.prototype.config, {
        Controller: ProjectGraphController,
    }),
});

viewRegistry.add('project_rating_graph', ProjectGraphView);

});
