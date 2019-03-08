odoo.define('hr_payroll.benefits_calendar', function(require) {
    'use strict';

    var core = require('web.core');
    var BenefitControllerMixin = require('hr_payroll.BenefitControllerMixin');
    var CalendarController = require("web.CalendarController");
    var CalendarModel = require('web.CalendarModel');
    var CalendarRenderer = require('web.CalendarRenderer');
    var CalendarView = require('web.CalendarView');
    var viewRegistry = require('web.view_registry');

    var _t = core._t;


    var BenefitCalendarController = CalendarController.extend(BenefitControllerMixin, {
        events: _.extend({}, CalendarController.prototype.events, {
            'click .btn-benefit-generate': '_onGenerateBenefits',
            'click .btn-benefit-validate': '_onValidateBenefits',
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

        _onGenerateBenefits: function (e) {
            e.preventDefault();
            e.stopImmediatePropagation();
            this._generateBenefits();
        },
        _onGeneratePayslips: function (e) {
            e.preventDefault();
            e.stopImmediatePropagation();
            this._generatePayslips();
        },
        _onValidateBenefits: function (e) {
            e.preventDefault();
            e.stopImmediatePropagation();
            this._validateBenefits();
        },
    });

    var BenefitCalendarModel = CalendarModel.extend({
         /**
          * Display everybody's benefits if no employee filter exists
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
                    all_filter.label = _t("Everybody's benefits");

                    if (filter.write_model && filter.filters.length <= 1 && all_filter.active === undefined) {
                        filter.all = true;
                        all_filter.active = true;
                    }
                }

            });
        }
    });

    var BenefitCalendarView = CalendarView.extend({
        config: _.extend({}, CalendarView.prototype.config, {
            Controller: BenefitCalendarController,
            Model: BenefitCalendarModel,
            Renderer: CalendarRenderer,
        }),
    });

    viewRegistry.add('benefits_calendar', BenefitCalendarView);
});
