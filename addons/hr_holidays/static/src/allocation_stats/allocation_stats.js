import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { useRecordObserver } from "@web/model/relational_model/utils";
import { Component, onWillStart, proxy } from "@odoo/owl";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";
import { KanbanMany2OneAvatarEmployeeField } from "@hr/views/fields/many2one_avatar_employee_field/kanban_many2one_avatar_employee_field";
const { DateTime } = luxon;

export class AllocationStatsComponent extends Component {
    static template = "hr_holidays.AllocationStatsComponent";
    static components = {
        KanbanMany2OneAvatarEmployeeField,
    };
    static props = { ...standardWidgetProps };

    setup() {
        this.orm = useService("orm");

        this.state = proxy({
            allocations: [],
            employee: null,
        });
        this.date_format = { year: "numeric", month: "2-digit", day: "2-digit" };
        this.state.employee = this.props.record.data.employee_id;

        onWillStart(async () => {
            await this.loadAllocations(this.state.employee);
        });

        useRecordObserver(async (record) => {
            const employee = record.data.employee_id;
            if (
                employee &&
                (this.state.employee && this.state.employee.id) !== employee.id
            ) {
                await this.loadAllocations(employee);
            }
            this.state.employee = employee;
        });
    }

    get thisYear() {
        return DateTime.now().toFormat("yyyy");
    }

    async loadAllocations(employee) {
        if (!employee) {
            this.state.allocations = [];
            return;
        }

        const now = DateTime.now();
        const dateFrom = now.startOf("year").toISODate();
        const dateTo = now.endOf("year").toISODate();
        const allocations = await this.orm.webSearchRead(
            "hr.leave.allocation",
            [
                ["employee_id", "=", employee.id],
                ["state", "in", ["validate", "confirm", "validate1"]],
                ["date_from", "<=", dateTo],
                "|",
                ["date_to", "=", false],
                ["date_to", ">=", dateFrom],
            ],
            {
                specification: {
                    work_entry_type_id: { fields: { display_name: {} } },
                    date_from: {},
                    date_to: {},
                    number_of_days: {},
                    number_of_hours_display: {},
                    type_request_unit: {},
                    accrual_plan_id: { fields: { display_name: {} } },
                },
            }
        );
        this.state.allocations = this.arrangeData(allocations.records);
    }

    arrangeData(allocations) {
        allocations.forEach((alloc) => {
            if (alloc.date_from) {
                const dateFrom = DateTime.fromISO(alloc.date_from);
                alloc.date_from_display = dateFrom.toLocaleString(this.date_format);
            }
            if (alloc.date_to) {
                const dateTo = DateTime.fromISO(alloc.date_to);
                alloc.date_to_display = dateTo.toLocaleString(this.date_format);
            }
            alloc.number_of_days = Number(alloc.number_of_days.toFixed(2));
        });
        return allocations;
    }
}

export const allocationStatsComponent = {
    component: AllocationStatsComponent,
    fieldDependencies: [
        { name: "employee_id", type: "many2one" },
    ],
};
registry.category("view_widgets").add("hr_allocation_stats", allocationStatsComponent);
