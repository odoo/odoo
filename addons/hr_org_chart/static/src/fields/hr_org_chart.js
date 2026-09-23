/** @odoo-module native */
import { rpc } from "@web/core/network";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { usePopover } from "@web/ui/popover";
import { user } from "@web/core/user";
import { onEmployeeSubRedirect } from "./hooks.js";
import { Component, useState } from "@odoo/owl";
import { standardFieldProps } from "@web/fields/standard_field_props";
import { useRecordObserver } from "@web/fields/hooks/record_observer";

class HrOrgChartPopover extends Component {
    static template = "hr_org_chart.hr_orgchart_emp_popover";
    static props = {
        employee: Object,
        close: Function,
    };
    async setup() {
        super.setup();

        this.orm = useService("orm");
        this.actionService = useService("action");
        this._onEmployeeSubRedirect = onEmployeeSubRedirect();
    }

    /**
     * @private
     * @param {number} employeeId
     */
    async _onEmployeeRedirect(employeeId) {
        const action = await this.orm.call("hr.employee", "get_formview_action", [
            employeeId,
        ]);
        this.actionService.doAction(action);
    }
}

export class HrOrgChart extends Component {
    static template = "hr_org_chart.hr_org_chart";
    static props = { ...standardFieldProps };
    async setup() {
        super.setup();

        this.orm = useService("orm");
        this.actionService = useService("action");
        this.popover = usePopover(HrOrgChartPopover);

        this.state = useState({ employee_id: null });
        this.chart = useState({
            managers: [],
            children: [],
            managers_more: false,
            self: null,
            view_employee_id: null,
            max_level: null,
        });
        this.lastEmployeeId = null;
        this._onEmployeeSubRedirect = onEmployeeSubRedirect();

        useRecordObserver(async (record) => {
            const newParentId = record.data.parent_id?.id || false;
            const newEmployeeId = record.resId || false;
            if (
                this.lastParent !== newParentId ||
                this.state.employee_id !== newEmployeeId
            ) {
                this.lastParent = newParentId;
                this.chart.max_level = null;
                await this.fetchEmployeeData(newEmployeeId, newParentId, true);
            }
            this.state.employee_id = newEmployeeId;
        });
    }

    async fetchEmployeeData(employeeId, newParentId = null, force = false) {
        if (!employeeId) {
            Object.assign(this.chart, {
                managers: [],
                children: [],
                view_employee_id: null,
            });
        } else if (employeeId !== this.chart.view_employee_id || force) {
            this.chart.view_employee_id = employeeId;
            const orgData = await rpc("/hr/get_org_chart", {
                employee_id: employeeId,
                new_parent_id: newParentId,
                context: {
                    ...user.context,
                    max_level: this.chart.max_level,
                },
            });
            Object.assign(this.chart, {
                managers: orgData.managers || [],
                children: orgData.children || [],
                managers_more: orgData.managers_more,
                self: orgData.self,
            });
        }
    }

    _onOpenPopover(event, employee) {
        this.popover.open(event.currentTarget, { employee });
    }

    /**
     * @private
     * @param {number} employeeId
     */
    async _onEmployeeRedirect(employeeId) {
        const action = await this.orm.call("hr.employee", "get_formview_action", [
            employeeId,
        ]);
        this.actionService.doAction(action);
    }

    async _onEmployeeMoreManager() {
        this.chart.max_level = 100;
        await this.fetchEmployeeData(this.state.employee_id, null, true);
    }
}

export const hrOrgChart = {
    component: HrOrgChart,
};

registry.category("fields").add("hr_org_chart", hrOrgChart);
