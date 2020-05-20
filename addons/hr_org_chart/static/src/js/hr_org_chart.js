odoo.define('web.OrgChart', function (require) {
    "use strict";

    const AbstractField = require('web.AbstractFieldOwl');
    const fieldRegistry = require('web.field_registry_owl');
    const session = require('web.session');

    class EmployeeChart extends owl.Component {
        async _onEmployeeRedirect(event) {
            const employeeID = $(event.currentTarget).data('employee-id');
            const action = await this.env.services.rpc({
                model: 'hr.employee',
                method: 'get_formview_action',
                args: [employeeID],
            });
            this.trigger('do-action', {action: action});
        }
    }
    EmployeeChart.template = "hr_org_chart_employee";

    class FieldOrgChart extends AbstractField {

        constructor(...args) {
            super(...args);
            this.employee = null;
        }

        async willStart() {
            if (!this.recordData.id) {
                this.orgData = {
                    managers: [],
                    children: [],
                };
                return;
            } else if (!this.employee) {
                // the widget is either dispayed in the context of a hr.employee form or a res.users form
                this.employee = this.recordData.employee_ids !== undefined ? this.recordData.employee_ids.res_ids[0] : this.recordData.id;
            }
            this.orgData = await this._getOrgData();
            if (_.isEmpty(this.orgData)) {
                this.orgData = {
                    managers: [],
                    children: [],
                };
            }
            this.orgData.view_employee_id = this.recordData.id;
        }

        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------
        /**
         * Get the chart data through a rpc call.
         *
         * @private
         * @param {integer} employee_id
         * @returns {Promise}
         */
        async _getOrgData() {
            this.employee = this.recordData.employee_ids !== undefined ? this.recordData.employee_ids.res_ids[0] : this.recordData.id;
            const data = await this.env.services.rpc({
                route: '/hr/get_org_chart',
                params: {
                    employee_id: this.employee,
                    context: session.user_context,
                },
            });
            return data;
        }
        /**
         * Get subordonates of an employee through a rpc call.
         *
         * @private
         * @param {integer} employee_id
         * @returns {Promise}
         */
        async _getSubordinatesData(employeeID, type) {
            const sunbordinates = await this.env.services.rpc({
                route: '/hr/get_subordinates',
                params: {
                    employee_id: employeeID,
                    subordinates_type: type,
                    context: session.user_context,
                },
            });
            return sunbordinates;
        }

        //--------------------------------------------------------------------------
        // Handlers
        //--------------------------------------------------------------------------

        _onEmployeeMoreManager(event) {
            event.preventDefault();
            this.employee = event.currentTarget.data('employee-id');
        }
        /**
         * Redirect to the employee form view.
         *
         * @private
         * @param {MouseEvent} event
         * @returns {Promise} action loaded
         */
        async _onEmployeeRedirect(event) {
            const employeeID = $(event.currentTarget).data('employee-id');
            const action = await this.env.services.rpc({
                model: 'hr.employee',
                method: 'get_formview_action',
                args: [employeeID],
            });
            this.trigger('do-action', {action: action});
        }
        /**
         * Redirect to the sub employee form view.
         *
         * @private
         * @param {MouseEvent} event
         * @returns {Promise} action loaded
         */
        async _onEmployeeSubRedirect(event) {
            const employeeID = $(event.currentTarget).data('employee-id');
            const type = $(event.currentTarget).data('type') || 'direct';
            if (employeeID) {
                const data = await this._getSubordinatesData(employeeID, type);
                const domain = [['id', 'in', data]];
                let action = await this.env.services.rpc({
                    model: 'hr.employee',
                    method: 'get_formview_action',
                    args: [employeeID],
                });
                action = Object.assign(action, {
                    'view_mode': 'kanban,list,form',
                    'views':  [[false, 'kanban'], [false, 'list'], [false, 'form']],
                    'domain': domain,
                });
                this.trigger('do-action', {action: action});
            }
        }
    }

    FieldOrgChart.template = "hr_org_chart";
    FieldOrgChart.components = { EmployeeChart };
    fieldRegistry.add('hr_org_chart', FieldOrgChart);

    return FieldOrgChart;

});
