import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { usePopover } from "@web/core/popover/popover_hook";
import { user } from "@web/core/user";
import { onEmployeeSubRedirect } from "./hooks";
import { Component, proxy } from "@odoo/owl";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { useRecordObserver } from "@web/model/relational_model/utils";

class HrOrgChartPopover extends Component {
    static template = "hr.hr_orgchart_emp_popover";
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
     * Redirect to the employee form view.
     *
     * @private
     * @param {MouseEvent} event
     * @returns {Promise} action loaded
     */
    async _onEmployeeRedirect(employeeId) {
        const action = await this.orm.call("hr.employee", "get_record_default_action", [
            employeeId,
        ]);
        this.actionService.doAction(action);
    }
}

export class HrOrgChart extends Component {
    static template = "hr.hr_org_chart";
    static props = { ...standardFieldProps };
    async setup() {
        super.setup();

        this.orm = useService("orm");
        this.actionService = useService("action");
        this.popover = usePopover(HrOrgChartPopover);

        this.state = proxy({
            employee_id: null,
            managers: [],
            children: [],
            managers_more: false,
            self: null,
        });
        this.max_level = null;
        this.lastEmployeeId = null;
        this.lastJobTitle = null;
        this._onEmployeeSubRedirect = onEmployeeSubRedirect();
        this.fetchId = 0;

        useRecordObserver(async (record) => {
            const newParentId = record.data.parent_id?.id || false;
            const newEmployeeId = record.resId || false;
            const newJobTitle = record.data.job_title || false;
            if (
                this.lastParent !== newParentId ||
                this.state.employee_id !== newEmployeeId ||
                this.lastJobTitle !== newJobTitle
            ) {
                this.lastParent = newParentId;
                this.max_level = null; // Reset max_level to default
                this.lastJobTitle = newJobTitle;
                await this.fetchEmployeeData(newEmployeeId, newParentId, newJobTitle, true);
            }
            this.state.employee_id = newEmployeeId;
        });
    }

    async fetchEmployeeData(employeeId, newParentId = null, newJobTitle = null, force = false) {
        this.fetchId++;
        const currentFetchId = this.fetchId;
        const updateData = (data) => {
            this.state.managers = data.managers || [];
            this.state.children = data.children || [];
            this.state.managers_more = data.managers_more;
            this.state.self = data.self;
        };
        if (!employeeId) {
            this.view_employee_id = null;
            this.state.managers = [];
            this.state.children = [];
        } else if (employeeId !== this.view_employee_id || force) {
            this.view_employee_id = employeeId;
            await rpc(
                "/hr/get_org_chart",
                {
                    employee_id: employeeId,
                    new_parent_id: newParentId,
                    new_job_title: newJobTitle,
                    context: {
                        ...user.context,
                        max_level: this.max_level,
                    },
                },
                {
                    cache: {
                        type: "disk",
                        update: "always",
                        callback: (freshData, hasChanged) => {
                            if (
                                hasChanged ||
                                currentFetchId !== this.fetchId ||
                                this.view_employee_id !== employeeId
                            ) {
                                return;
                            }
                            updateData(freshData);
                        },
                    },
                }
            ).then(updateData);
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
        const action = await this.orm.call("hr.employee", "get_record_default_action", [
            employeeId,
        ]);
        this.actionService.doAction(action);
    }

    async _onEmployeeMoreManager(managerId) {
        this.max_level = 100; // Set a high level to fetch all managers
        await this.fetchEmployeeData(this.state.employee_id, null, true);
    }
}

export const hrOrgChart = {
    component: HrOrgChart,
};

registry.category("fields").add("hr_org_chart", hrOrgChart);
