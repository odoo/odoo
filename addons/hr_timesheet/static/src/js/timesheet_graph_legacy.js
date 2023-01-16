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
            const currentCompanyId = session.user_context.allowed_company_ids[0];
            const currentCompany = session.user_companies.allowed_companies[currentCompanyId];
            const currentCompanyTimesheetUOMFactor = currentCompany.timesheet_uom_factor || 1;
            const fields = ['unit_amount', 'effective_hours', 'planned_hours', 'remaining_hours', 'total_hours_spent', 'subtask_effective_hours',
            'overtime', 'number_hours', 'difference', 'hours_effective', 'hours_planned', 'timesheet_unit_amount'];

            if (fields.includes(this.chart.measure) && currentCompanyTimesheetUOMFactor !== 1) {
                // recalculate the Duration values according to the timesheet_uom_factor
                this.chart.dataPoints.forEach(function (dataPt) {
                    dataPt.value *= currentCompanyTimesheetUOMFactor;
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
