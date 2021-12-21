odoo.define('hr_attendance.kiosk_mode', function (require) {
"use strict";

var AbstractAction = require('web.AbstractAction');
var ajax = require('web.ajax');
var core = require('web.core');
var Session = require('web.session');

var QWeb = core.qweb;


var KioskMode = AbstractAction.extend({
    events: {
        "click .o_hr_attendance_button_employees": function() {
            this.do_action('hr_attendance.hr_employee_attendance_action_kanban', {
                additional_context: {'no_group_by': true},
            });
        },
    },

    start: function () {
        var self = this;
        core.bus.on('barcode_scanned', this, this._onBarcodeScanned);
        self.session = Session;
        const company_id = this.session.user_context.allowed_company_ids[0];
        var def = this._rpc({
                model: 'res.company',
                method: 'search_read',
                args: [[['id', '=', company_id]], ['name']],
            })
            .then(function (companies){
                self.company_name = companies[0].name;
                self.company_image_url = self.session.url('/web/image', {model: 'res.company', id: company_id, field: 'logo',});
                self.$el.html(QWeb.render("HrAttendanceKioskMode", {widget: self}));
                self.start_clock();
            });
        // Make a RPC call every day to keep the session alive
        self._interval = window.setInterval(this._callServer.bind(this), (60*60*1000*24));
        return Promise.all([def, this._super.apply(this, arguments)]);
    },

    on_attach_callback: function () {
        // Stop polling to avoid notifications in kiosk mode
        this.call('bus_service', 'stopPolling');
        $('body').find('.o_ChatWindowHeader_commandClose').click();
    },

    _onBarcodeScanned: function(barcode) {
        var self = this;
        core.bus.off('barcode_scanned', this, this._onBarcodeScanned);
        this._rpc({
                model: 'hr.employee',
                method: 'attendance_scan',
                args: [barcode, ],
            })
            .then(function (result) {
                if (result.action) {
                    self.do_action(result.action);
                } else if (result.warning) {
                    self.do_warn(result.warning);
                    core.bus.on('barcode_scanned', self, self._onBarcodeScanned);
                }
            }, function () {
                core.bus.on('barcode_scanned', self, self._onBarcodeScanned);
            });
    },

    start_clock: function() {
        this.clock_start = setInterval(function() {this.$(".o_hr_attendance_clock").text(new Date().toLocaleTimeString(navigator.language, {hour: '2-digit', minute:'2-digit', second:'2-digit'}));}, 500);
        // First clock refresh before interval to avoid delay
        this.$(".o_hr_attendance_clock").show().text(new Date().toLocaleTimeString(navigator.language, {hour: '2-digit', minute:'2-digit', second:'2-digit'}));
    },

    destroy: function () {
        core.bus.off('barcode_scanned', this, this._onBarcodeScanned);
        clearInterval(this.clock_start);
        clearInterval(this._interval);
        this.call('bus_service', 'startPolling');
        this._super.apply(this, arguments);
    },

    _callServer: function () {
        // Make a call to the database to avoid the auto close of the session
        return ajax.rpc("/hr_attendance/kiosk_keepalive", {});
    },

});

core.action_registry.add('hr_attendance_kiosk_mode', KioskMode);

return KioskMode;

});
