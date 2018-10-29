odoo.define('hr_payroll.benefit.view_custo', function(require) {
    'use strict';

    var core = require('web.core');
    var CalendarController = require("web.CalendarController");

    var _t = core._t;
    CalendarController.include({

        update: function () {
            var self = this;
            return this._super.apply(this, arguments).then(function () {
                self._renderBenefitButtons();
            });
        },

        _renderGenerateButton: function(date_from, date_to, employee_ids, secondary) {
            var self = this;
            var primary = !secondary ? 'btn-primary' : 'btn-secondary';
            var txt = _t("Generate Benefits");
            this.$buttons.find('.o_calendar_button_month').after(
                $('<button class="btn ' + primary + ' btn-benefit" type="button">'+ txt +'</button>')
                .off('click')
                .on('click', function (e) {
                    e.preventDefault();
                    e.stopImmediatePropagation();
                    var date_fmt = 'YYYY-MM-DD HH:mm:ss';
                    var options = {
                        on_close: function () {
                            self.reload();
                        },
                    };
                    self.do_action({
                        type: 'ir.actions.act_window',
                        name: txt,
                        res_model: 'hr.benefit.employees',
                        view_type: 'form',
                        views: [[false,'form']],
                        target: 'new',
                        context: {
                            'start_benefits': date_from.format(date_fmt),
                            'stop_benefits':date_to.format(date_fmt),
                        },
                    }, options);
                })
            );
        },

        _renderBenefitButtons: function () {
            if (this.modelName !== "hr.benefit") {
                return;
            }

            var firstDay = this.model.data.target_date.clone().startOf('month');
            var lastDay = this.model.data.target_date.clone().endOf('month');
            var events = this._checkDataInRange(firstDay, lastDay, this.model.data.data);
            var is_validated = this._checkValidation(events);
            this.$buttons.find('.btn-benefit').remove();
            var employee_ids = _.map(events, function (event) { return event.record.employee_id[0]; });
            employee_ids = _.uniq(employee_ids);
            var self = this;
            if (this.model.data.domain.length !== 0) { // select by default the employee in the domain
                var employee_search_id = (this.model.data.domain[0][0] === 'employee_id' &&  this.model.data.domain[0][1] === '=')? [this.model.data.domain[0][2]]: null;
            }
            if (events.length === 0) { // Generate button
                this._renderGenerateButton(firstDay, lastDay, employee_search_id);
            } else {
                this._renderGenerateButton(firstDay, lastDay, employee_ids, true);
            }
            if (is_validated && events.length !== 0) { // Generate Payslip button
                this.$buttons.find('.o_calendar_button_month').after(
                    $('<button class="btn btn-primary btn-benefit" type="button">'+ _t('Generate Payslips') +'</button>')
                    .off('click')
                    // action_hr_payslip_by_employees
                    .on('click', function (e) {
                        e.preventDefault();
                        e.stopImmediatePropagation();
                        var date_fmt = 'YYYY-MM-DD';
                        self.do_action('hr_payroll.action_hr_payslip_by_employees', {
                            additional_context: {
                                default_employee_ids: employee_ids || [],
                                default_date_start: firstDay.format(date_fmt),
                                default_date_end: lastDay.format(date_fmt),
                            },
                        });
                    })
                );
            }
            else if (!is_validated) { // Validate button
                this.$buttons.find('.o_calendar_button_month').after(
                    $('<button class="btn btn-primary btn-benefit" type="button">'+ _t('Validate Benefits') +'</button>')
                    .off('click')
                    .on('click', function (e) {
                        e.preventDefault();
                        e.stopImmediatePropagation();
                        self._rpc({
                            model: 'hr.benefit',
                            method: 'action_validate',
                            args: [_.map(events, function (event) { return event.record.id; })],
                        }).then(function () {
                            return self.reload();
                        });
                    })
                );
            }
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
});