odoo.define('hr_timesheet.GridRenderer', function (require) {
    "use strict";

    var WebGridRenderer = require('web_grid.GridRenderer');
    var session = require('web.session');

    return WebGridRenderer.include({
        init: function(parent, state, params){
            // force factor in format and parse options
            if (session.timesheet_uom_factor && params.cellWidget == 'timesheet_uom') {
                if (!(params.cellWidgetOptions)){
                    params.cellWidgetOptions = {};
                }
                if (!(params.cellWidgetOptions.factor)){
                    params.cellWidgetOptions.factor = session.timesheet_uom_factor;
                }
            }
            this._super.apply(this,arguments);
        }
    });

});