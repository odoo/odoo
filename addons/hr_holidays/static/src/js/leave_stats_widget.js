odoo.define('hr_holidays.LeaveStatsWidget', function (require) {
    "use strict";

    var time = require('web.time');
    var Widget = require('web.Widget');
    var widget_registry = require('web.widget_registry');

    var LeaveStatsWidget = Widget.extend({
        template: 'hr_holidays.leave_stats',

        /**
         * @override
         * @param {Widget|null} parent
         * @param {Object} params
         */
        init: function (parent, params) {
            this._setState(params);
            this._super(parent);
        },

        //--------------------------------------------------------------------------
        // Public
        //--------------------------------------------------------------------------

        /**
         * @override to fetch data before rendering.
         */
        willStart: function () {
            return Promise.all([this._super(), this._fetchLeaveTypesData(), this._fetchDepartmentLeaves()]);
        },

        /**
         * Fetch new data if needed (according to updated fields) and re-render the widget.
         * Called by the basic renderer when the view changes.
         * @param {Object} state
         * @returns {Promise}
         */
        updateState: function (state) {
            var self = this;
            var to_await = [];
            var updatedFields = this._setState(state);

            if (_.intersection(updatedFields, ['employee', 'date']).length) {
                to_await.push(this._fetchLeaveTypesData());
            }
            if (_.intersection(updatedFields, ['department', 'date']).length) {
                to_await.push(this._fetchDepartmentLeaves());
            }
            return Promise.all(to_await).then(function () {
                self.renderElement();
            });
        },

        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------

        /**
         * Update the state
         * @param {Object} state
         * @returns {String[]} list of updated fields
         */
        _setState: function (state) {
            var updatedFields = [];
            if (state.data.employee_id.res_id !== (this.employee && this.employee.res_id)) {
                updatedFields.push('employee');
                this.employee = state.data.employee_id;
            }
            if (state.data.department_id.res_id !== (this.department && this.department.res_id)) {
                updatedFields.push('department');
                this.department = state.data.department_id;
            }
            if (state.data.date_from !== this.date) {
                updatedFields.push('date');
                this.date = state.data.date_from;
            }
            return updatedFields;
        },

        /**
         * Fetch leaves taken by members of ``this.department`` in the
         * month of ``this.date``.
         * Three fields are fetched for each leave, namely: employee_id, date_from
         * and date_to.
         * The resulting data is assigned to ``this.departmentLeaves``
         * @private
         * @returns {Promise}
         */
        _fetchDepartmentLeaves: function () {
            if (!this.date || !this.department) {
                this.departmentLeaves = null;
                return Promise.resolve();
            }
            var self = this;
            var month_date_from = this.date.clone().startOf('month');
            var month_date_to = this.date.clone().endOf('month');
            return this._rpc({
                model: 'hr.leave',
                method: 'search_read',
                args: [
                    [['department_id', '=', this.department.res_id],
                    ['state', '=', 'validate'],
                    ['holiday_type', '=', 'employee'],
                    ['date_from', '<=', month_date_to],
                    ['date_to', '>=', month_date_from]],
                    ['employee_id', 'date_from', 'date_to', 'number_of_days'],
                ],
            }).then(function (data) {
                var dateFormat = time.getLangDateFormat();
                self.departmentLeaves = data.map(function (leave) {
                    // Format datetimes to date (in the user's format)
                    return _.extend(leave, {
                        date_from: moment(leave.date_from).format(dateFormat),
                        date_to: moment(leave.date_to).format(dateFormat),
                        number_of_days: leave.number_of_days,
                    });
                });
            });
        },

        /**
         * Fetch the number of leaves, grouped by leave type, taken by ``this.employee``
         * in the year of ``this.date``.
         * The resulting data is assigned to ``this.leavesPerType``
         * @private
         * @returns {Promise}
         */
        _fetchLeaveTypesData: function () {
            if (!this.date || !this.employee) {
                this.leavesPerType = null;
                return Promise.resolve();
            }
            var self = this;
            var year_date_from = this.date.clone().startOf('year');
            var year_date_to = this.date.clone().endOf('year');
            return this._rpc({
                model: 'hr.leave',
                method: 'read_group',
                kwargs: {
                    domain: [['employee_id', '=', this.employee.res_id], ['state', '=', 'validate'], ['date_from', '<=', year_date_to], ['date_to', '>=', year_date_from]],
                    fields: ['holiday_status_id', 'number_of_days:sum'],
                    groupby: ['holiday_status_id'],
                },
            }).then(function (data) {
                self.leavesPerType = data;
            });
        }
    });

    widget_registry.add('hr_leave_stats', LeaveStatsWidget);

    return LeaveStatsWidget;
});
