odoo.define('hr_payroll.benefit.view_custo', function(require) {
    'use strict';

    var core = require('web.core');
    var CalendarController = require("web.CalendarController");
    var time = require('web.time');
    var CalendarModel = require('web.CalendarModel');
    var CalendarRenderer = require('web.CalendarRenderer');
    var CalendarView = require('web.CalendarView');
    var viewRegistry = require('web.view_registry');
    var _t = core._t;
    var BenefitCalendarController = CalendarController.extend({

        events: {
            'click .btn-benefit-generate': '_onGenerateBenefits',
            'click .btn-benefit-validate': '_onValidateBenefits',
            'click .btn-payslip-generate': '_onGeneratePayslips',
        },

        update: function () {
            var self = this;
            return this._super.apply(this, arguments).then(function () {
                self._renderBenefitButtons();
            });
        },

        _renderBenefitButton: function (text, event_class) {
            var $button = $('<button class="btn btn-primary btn-benefit" type="button" />');
            $button.text(text).addClass(event_class);
            this.$buttons.find('.o_calendar_button_month').after($button);
        },

        _renderBenefitButtons: function () {
            if (this.modelName !== "hr.benefit") {
                return;
            }

            this.firstDay = this.model.data.target_date.clone().startOf('month').toDate();
            this.lastDay = this.model.data.target_date.clone().endOf('month').toDate();
            this.events = this._checkDataInRange(this.firstDay, this.lastDay, this.model.data.data);
            var is_validated = this._checkValidation(this.events);
            this.$buttons.find('.btn-benefit').remove();
            if (this.events.length === 0) {
                this._renderBenefitButton(_t("Generate Benefits"), 'btn-benefit-generate');
            }
            if (is_validated && this.events.length !== 0) {
                this._renderBenefitButton(_t("Generate Payslips"), 'btn-payslip-generate');
            }
            else if (!is_validated) {
                this._renderBenefitButton(_t("Validate Benefits"), 'btn-benefit-validate');
            }
        },

        _onGeneratePayslips: function (e) {
            e.preventDefault();
            e.stopImmediatePropagation();
            this.do_action('hr_payroll.action_generate_payslips_from_benefits', {
                additional_context: {
                    default_date_start: time.datetime_to_str(this.firstDay),
                    default_date_end: time.datetime_to_str(this.lastDay),
                },
            });
        },

        _onValidateBenefits: function (e) {
            e.preventDefault();
            e.stopImmediatePropagation();
            var self = this;
            this._rpc({
                model: 'hr.benefit',
                method: 'action_validate',
                args: [_.map(this.events, function (event) { return event.record.id; })],
            }).then(function () {
                return self.reload();
            });
        },

        _onGenerateBenefits: function (e) {
            e.preventDefault();
            e.stopImmediatePropagation();
            var self = this;
            this._rpc({
                model: 'hr.employee',
                method: 'generate_benefit',
                args: [time.datetime_to_str(this.firstDay), time.datetime_to_str(this.lastDay)],
            }).then(function () {
                self.reload();
            });
        },

        _checkDataInRange: function (firstDay, lastDay, events) {
            var res = _.filter(events, function (event) {
                // Filter records that are not inside the current month
                // (because in calendar view some days of prev. and next month are visible)
                return event.record.date_start.isBefore(lastDay) && event.record.date_stop.isAfter(firstDay);
            });
            return res;
        },

        _checkValidation: function (records) {
            return _.every(records, function (record) {
                return record.record.state === 'validated';
            });
        },

        renderButtons: function () {
            this._super.apply(this, arguments);
            this._renderBenefitButtons();
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