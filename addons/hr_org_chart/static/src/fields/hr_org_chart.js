/** @odoo-module */

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { usePopover } from "@web/core/popover/popover_hook";
import { onEmployeeSubRedirect } from './hooks';
import { Component, onWillStart, useState } from "@odoo/owl";
import { useRecordObserver } from "@web/model/relational_model/utils";

class HrOrgChartPopover extends Component {
    async setup() {
        super.setup();

        this.rpc = useService('rpc');
        this.orm = useService('orm');
        this.actionService = useService("action");
        this._onEmployeeSubRedirect = onEmployeeSubRedirect();
    }

    /**
     * Redirect to the employee form view.
     *
     * @private
     * @param {MouseEvent} event
     * @returns {Promise} action loaded
     */
    async _onEmployeeRedirect(employeeId) {
        const action = await this.orm.call('hr.employee', 'get_formview_action', [employeeId]);
        this.actionService.doAction(action); 
    }
}
HrOrgChartPopover.template = 'hr_org_chart.hr_orgchart_emp_popover';

export class HrOrgChart extends Component {
    async setup() {
        super.setup();

        this.rpc = useService('rpc');
        this.orm = useService('orm');
        this.actionService = useService("action");
        this.user = useService("user");
        this.popover = usePopover(HrOrgChartPopover);

        this.state = useState({'employee_id': null});
        this.lastParent = null;
        this.max_level = null;
        this._onEmployeeSubRedirect = onEmployeeSubRedirect();

        onWillStart(async () => {
            this.employee = this.props.record.data;
            // the widget is either dispayed in the context of a hr.employee form or a res.users form
            this.state.employee_id =
                this.employee.employee_ids !== undefined
                    ? this.employee.employee_ids.resIds[0]
                    : this.props.record.resId;
            const parentId =
                this.employee.parent_id && this.employee.parent_id[0]
                    ? this.employee.parent_id[0]
                    : false;
            const forceReload =
                this.lastRecord !== this.props.record || this.lastParent != parentId;
            this.lastParent = parentId;
            this.lastRecord = this.props.record;
            await this.fetchEmployeeData(this.state.employee_id, forceReload);
        });

        useRecordObserver(async (record) => {
            const newParentId =
                record.data.parent_id && record.data.parent_id[0]
                    ? record.data.parent_id[0]
                    : false;
            const newEmployeeId = record.data.id || false;
            if (this.lastParent !== newParentId || this.state.employee_id !== newEmployeeId) {
                this.lastParent = newParentId;
                this.max_level = null; // Reset max_level to default
                await this.fetchEmployeeData(newEmployeeId, true);
            }
            this.state.employee_id = newEmployeeId;
        });
    }

    async fetchEmployeeData(employeeId, force = false) {
        if (!employeeId) {
            this.managers = [];
            this.children = [];
            if (this.view_employee_id) {
                this.render(true);
            }
            this.view_employee_id = null;
        } else if (employeeId !== this.view_employee_id || force) {
            this.view_employee_id = employeeId;
            let orgData = await this.rpc(
                '/hr/get_org_chart',
                {
                    employee_id: employeeId,
                    context: {
                        ...this.user.context,
                    max_level: this.max_level,
                    new_parent_id: this.lastParent,
                },
            });
            if (Object.keys(orgData).length === 0) {
                orgData = {
                    managers: [],
                    children: [],
                }
            }
            this.managers = orgData.managers;
            this.children = orgData.children;
            this.managers_more = orgData.managers_more;
            this.self = orgData.self;
            this.render(true);
        }
    }

    _onOpenPopover(event, employee) {
        this.popover.open(event.currentTarget, { employee });
    }

    /**
     * Redirect to the employee form view.
     *
     * @private
     * @param {MouseEvent} event
     * @returns {Promise} action loaded
     */
    async _onEmployeeRedirect(employeeId) {
        const action = await this.orm.call('hr.employee', 'get_formview_action', [employeeId]);
        this.actionService.doAction(action); 
    }

    async _onEmployeeMoreManager(managerId) {
        this.max_level = 100; // Set a high level to fetch all managers
        await this.fetchEmployeeData(this.state.employee_id, true);
    }
}

HrOrgChart.template = 'hr_org_chart.hr_org_chart';

export const hrOrgChart = {
    component: HrOrgChart,
};

registry.category("fields").add("hr_org_chart", hrOrgChart);
