odoo.define('planner_barcode.planner', function (require) {
"use strict";

var planner = require('web.planner.common');

planner.PlannerDialog.include({
    prepare_planner_event: function() {
        var self = this;
        this._super.apply(this, arguments);
        if(self.planner['planner_application'] == 'planner_barcode') {
            self.$el.on('keypress', '.barcode-scanner', function(ev) {
                self.$('.carriage-return').addClass('show').removeClass('hide');
                if(ev.which == 13) {
                    self.$('.carriage-return span').text('ON').removeClass('label-danger').addClass('label-success');
                } else {
                    self.$('.carriage-return span').text('OFF').removeClass('label-success').addClass('label-danger');
                }
            });
        }
    }
});

});
