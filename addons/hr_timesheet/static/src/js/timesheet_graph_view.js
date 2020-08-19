odoo.define('hr_timesheet.timesheet_graph_view', function (require) {
    "use strict";

    const GraphView = require('web.GraphView');
    var viewRegistry = require('web.view_registry');
    
    const TimesheetGraphView = GraphView.extend({
        /**
         * @override
         */
        init: function (viewInfo, params) {
            this._super.apply(this, arguments);

            this.loadParams.fields["unit_amount"].string = this.controllerParams.measures[0].description;
            this.loadParams.fields["amount"].string = this.controllerParams.measures[1].description;
        }    
    });

    viewRegistry.add('timesheet_graph_view', TimesheetGraphView);

    return { TimesheetGraphView };
});
