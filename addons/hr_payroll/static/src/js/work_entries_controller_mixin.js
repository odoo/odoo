odoo.define('hr_payroll.WorkEntryControllerMixin', function(require) {
    'use strict';

    var core = require('web.core');
    var time = require('web.time');

    var _t = core._t;
    var QWeb = core.qweb;

    /*
        This mixin implements the behaviours necessary to generate and validate work entries and Payslips
        It is intended to be used in a Controller and requires three methods to be defined on your Controller

         1. _fetchRecords
            Which should return a list of records containing at least the state and id fields

         2. _fetchFirstDay
            Which should return the first day for which we will generate the work entries, it should be a Moment instance
            (Typically the first day of the current month)

         3. _fetchLastDay
            Same as _fetchFirstDay except that this is the last day of the period

        This mixin is responsible for rendering the buttons in the control panel and adds the three following methods

        1. _generateWorkEntries
        2. _generatePayslips
        3. _validateWorkEntries
    */

    var WorkEntryControllerMixin = {
        /*
            Overrides of Controller methods
        */
        renderButtons: function () {
            this._super.apply(this, arguments);
            this._renderWorkEntryButtons();
        },

        _update: function () {
            var self = this;
            return this._super.apply(this, arguments).then(function () {
                self.firstDay = self._fetchFirstDay().toDate();
                self.lastDay = self._fetchLastDay().toDate();
                self._renderWorkEntryButtons();
            });
        },

        /*
            Private
        */

        _generateWorkEntries: function () {
            var self = this;
            this._rpc({
                model: 'hr.employee',
                method: 'generate_work_entry',
                args: [time.datetime_to_str(this.firstDay), time.datetime_to_str(this.lastDay)],
            }).then(function () {
                self.reload();
            });
        },

        _generatePayslips: function () {
            this.do_action('hr_payroll.action_generate_payslips_from_work_entries', {
                additional_context: {
                    default_date_start: time.datetime_to_str(this.firstDay),
                    default_date_end: time.datetime_to_str(this.lastDay),
                },
            });
        },

        _renderWorkEntryButtons: function () {
            if (this.modelName !== "hr.work.entry") {
                return;
            }

            var records = this._fetchRecords();
            var isvalidated = _.every(records, function (record) {
                return record.state === 'validated';
            });

            this.$buttons.find('.btn-work-entry').remove();

            var text = '';
            var cl = '';

            if (records.length === 0) {
                text = _t("Generate Work Entries");
                cl = 'btn-work-entry-generate';
            }
            else if (isvalidated && records.length !== 0) {
                text = _t("Generate Payslips");
                cl = 'btn-payslip-generate';
            }
            else if (!isvalidated) {
                text = _t("Validate Work Entries");
                cl = 'btn-work-entry-validate';
            }

            this.$buttons.append(QWeb.render('hr_payroll.work_entry_button', {
                button_text: text,
                event_class: cl,
            }));
        },

        _validateWorkEntries: function () {
            var self = this;
            var records = this._fetchRecords();
            this._rpc({
                model: 'hr.work.entry',
                method: 'action_validate',
                args: [_.map(records, function (record) { return record.id; })],
            }).then(function () {
                return self.reload();
            });
        },
    };

    return WorkEntryControllerMixin;

});
