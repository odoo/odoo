odoo.define('hr_attendance.kiosk_mode', function (require) {
"use strict";

var core = require('web.core');
var Widget = require('web.Widget');
var Session = require('web.session');
var BarcodeHandlerMixin = require('barcodes.BarcodeHandlerMixin');
var QWeb = core.qweb;


var KioskMode = Widget.extend(BarcodeHandlerMixin, {
    events: {
        "click .o_hr_attendance_button_employees": function(){ this.do_action('hr_attendance.hr_employee_attendance_action_kanban'); },
    },

    init: function (parent, action) {
        // Note: BarcodeHandlerMixin.init calls this._super.init, so there's no need to do it here.
        // Yet, "_super" must be present in a function for the class mechanism to replace it with the actual parent method.
        this._super;
        BarcodeHandlerMixin.init.apply(this, arguments);
    },

    start: function () {
        var self = this;
        self.session = Session;
        this._rpc('res.company', 'search_read')
            .args([[['id', '=', self.session.company_id]], ['name']])
            .exec()
            .then(function (companies){
                self.company_name = companies[0].name;
                self.company_image_url = self.session.url('/web/image', {model: 'res.company', id: self.session.company_id, field: 'logo',});
                self.$el.html(QWeb.render("HrAttendanceKioskMode", {widget: self}));
                self.start_clock();
            });
        return self._super.apply(this, arguments);
    },

    on_barcode_scanned: function(barcode) {
        var self = this;
        this._rpc('hr.employee', 'attendance_scan')
            .args([barcode, ])
            .exec()
            .then(function (result) {
                if (result.action) {
                    self.do_action(result.action);
                } else if (result.warning) {
                    self.do_warn(result.warning);
                }
            });
    },

    start_clock: function() {
        this.clock_start = setInterval(function() {this.$(".o_hr_attendance_clock").text(new Date().toLocaleTimeString(navigator.language, {hour: '2-digit', minute:'2-digit'}));}, 500);
        // First clock refresh before interval to avoid delay
        this.$(".o_hr_attendance_clock").text(new Date().toLocaleTimeString(navigator.language, {hour: '2-digit', minute:'2-digit'}));
    },

    destroy: function () {
        clearInterval(this.clock_start);
        this._super.apply(this, arguments);
    },
});

core.action_registry.add('hr_attendance_kiosk_mode', KioskMode);

return KioskMode;

});
