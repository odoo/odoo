odoo.define('hr_timesheet.GraphView', function (require) {
    "use strict";

    const viewRegistry = require('web.view_registry');
    const GraphView = require('web.GraphView');
    const GraphModel = require('web.GraphModel');

    const hrTimesheetGraphModel = GraphModel.extend({
        /*
         * Override the _processData to take into account the analytic line uom.
         */
        _processData: function (originIndex, rawData) {
            this._super.apply(this, arguments);
            const session = this.getSession();
            if (this.chart.measure === 'unit_amount' && session.timesheet_uom_factor !== 1) {
                // recalculate the Duration values according to the timesheet_uom_factor
                this.chart.dataPoints.forEach(function (dataPt) {
                    dataPt.value *= session.timesheet_uom_factor;
                });
            }
        },
    });


    const hrTimesheetGraphView = GraphView.extend({
        config: Object.assign({}, GraphView.prototype.config, {
            Model: hrTimesheetGraphModel,
        }),
    });

    viewRegistry.add('hr_timesheet_graphview', hrTimesheetGraphView);
    return hrTimesheetGraphView;
});

