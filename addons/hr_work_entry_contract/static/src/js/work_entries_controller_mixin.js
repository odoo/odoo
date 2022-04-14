odoo.define('hr_work_entry_contract.WorkEntryControllerMixin', function(require) {
    'use strict';

    var core = require('web.core');
    var time = require('web.time');

    var _t = core._t;
    var QWeb = core.qweb;

    /*
        This mixin implements the behaviours necessary to generate and validate work entries and Payslips
        It is intended to be used in a Controller and requires four methods to be defined on your Controller

         1. _fetchRecords
            Which should return a list of records containing at least the state and id fields

         2. _fetchFirstDay
            Which should return the first day for which we will generate the work entries, it should be a Moment instance
            (Typically the first day of the current month)

         3. _fetchLastDay
            Same as _fetchFirstDay except that this is the last day of the period

         4. _displayWarning
            Which should insert in the DOM the warning rendered template received as argument.

        This mixin is responsible for rendering the buttons in the control panel and adds the two following methods

        1. _generateWorkEntries
    */

    var WorkEntryControllerMixin = {

        /**
         * @override
         * @returns {Promise}
         */
        _update: function () {
            var self = this;
            return this._super.apply(this, arguments).then(function () {
                self.firstDay = self._fetchFirstDay().toDate();
                self.lastDay = self._fetchLastDay().toDate();
                var now = moment();
                if (self.firstDay > now.add(1, 'months')) return Promise.resolve();
                return self._generateWorkEntries();
            });
        },

        updateButtons: function() {
            this._super.apply(this, arguments);

            if(!this.$buttons) {
                return;
            }

            this.$buttons.find('.btn-regenerate-work-entries').on('click', this._onRegenerateWorkEntries.bind(this));
        },

        renderButtons: function($node) {
            this._super.apply(this, arguments);

            if(this.$buttons) {
                this.$buttons.append(this._renderWorkEntryButtons());
            }
        },

        /*
            Private
        */
        _renderWorkEntryButtons: function() {
            return $('<span>').append(QWeb.render('hr_work_entry.work_entry_button', {
                button_text: _t("Regenerate Work Entries"),
                event_class: 'btn-regenerate-work-entries',
            }));
        },

        _generateWorkEntries: function () {
            var self = this;
            return this._rpc({
                model: 'hr.employee',
                method: 'generate_work_entries',
                args: [[], time.date_to_str(this.firstDay), time.date_to_str(this.lastDay)],
            }).then(function (new_work_entries) {
                if (new_work_entries) {
                    self.reload();
                }
            });
        },

        _regenerateWorkEntries: function () {
            const all_rows = Object.values(this.model.allRows);
            const only_employee = all_rows.length === 1 ? all_rows[0].resId : null;
            this.do_action('hr_work_entry_contract.hr_work_entry_regeneration_wizard_action', {
                additional_context: {
                    default_employee_id: only_employee,
                    date_start: time.date_to_str(this.firstDay),
                    date_end: time.date_to_str(this.lastDay),
                },
                on_close: this.reload.bind(this),
            });
        },

        _onRegenerateWorkEntries: function (e) {
            e.preventDefault();
            e.stopImmediatePropagation();
            this._regenerateWorkEntries();
        },

    };

    return WorkEntryControllerMixin;

});
