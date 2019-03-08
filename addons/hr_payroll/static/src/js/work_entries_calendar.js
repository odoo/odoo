odoo.define('hr_payroll.work_entries_calendar', function(require) {
    'use strict';

    var core = require('web.core');
    var WorkEntryControllerMixin = require('hr_payroll.WorkEntryControllerMixin');
    var CalendarController = require("web.CalendarController");
    var CalendarModel = require('web.CalendarModel');
    var CalendarRenderer = require('web.CalendarRenderer');
    var CalendarView = require('web.CalendarView');
    var viewRegistry = require('web.view_registry');

    var _t = core._t;


    var WorkEntryCalendarController = CalendarController.extend(WorkEntryControllerMixin, {
        events: _.extend({}, CalendarController.prototype.events, {
            'click .btn-work-entry-generate': '_onGenerateWorkEntries',
            'click .btn-work-entry-validate': '_onValidateWorkEntries',
            'click .btn-payslip-generate': '_onGeneratePayslips',
        }),

        // Returns the records from the model
        _fetchRecords: function () {
            var self = this;
            var records = _.filter(this.model.data.data, function (data) {
                // Filter records that are not inside the current month
                // (because in calendar view some days of prev. and next month are visible)
                return data.record.date_start.isBefore(self.lastDay) && data.record.date_stop.isAfter(self.firstDay);
            });
            return _.pluck(records, 'record');
        },
        _fetchFirstDay: function () {
            return this.model.data.target_date.clone().startOf('month');
        },
        _fetchLastDay: function () {
            return this.model.data.target_date.clone().endOf('month');
        },

        /*
            Event handlers
        */

        _onGenerateWorkEntries: function (e) {
            e.preventDefault();
            e.stopImmediatePropagation();
            this._generateWorkEntries();
        },
        _onGeneratePayslips: function (e) {
            e.preventDefault();
            e.stopImmediatePropagation();
            this._generatePayslips();
        },
        _onValidateWorkEntries: function (e) {
            e.preventDefault();
            e.stopImmediatePropagation();
            this._validateWorkEntries();
        },
    });

    var WorkEntryCalendarModel = CalendarModel.extend({
         /**
          * Display everybody's work entries if no employee filter exists
          * @private
          * @override
          * @param {any} filter
          * @returns {Deferred}
         */
        _loadFilter: function (filter) {
            return this._super.apply(this, arguments).then(function () {
                var filters = filter.filters;
                var all_filter = filters[filters.length - 1];

                if (all_filter) {
                    all_filter.label = _t("Everybody's work entries");

                    if (filter.write_model && filter.filters.length <= 1 && all_filter.active === undefined) {
                        filter.all = true;
                        all_filter.active = true;
                    }
                }

            });
        }
    });

    var WorkEntryCalendarView = CalendarView.extend({
        config: _.extend({}, CalendarView.prototype.config, {
            Controller: WorkEntryCalendarController,
            Model: WorkEntryCalendarModel,
            Renderer: CalendarRenderer,
        }),
    });

    viewRegistry.add('work_entries_calendar', WorkEntryCalendarView);
});
