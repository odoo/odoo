import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { useRecordObserver } from "@web/model/relational_model/utils";
import { Component, onWillStart, proxy, useProps } from "@odoo/owl";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";
import { formatFloatTime } from "@web/views/fields/formatters";
const { DateTime } = luxon;

export class AllocationStatsComponent extends Component {
    static template = "hr_holidays.AllocationStatsComponent";
    props = useProps({ ...standardWidgetProps });

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
                ["state", "=", "validate"],
                ["date_from", "<=", dateTo],
                "|",
                ["date_to", "=", false],
                ["date_to", ">=", dateFrom],
            ],
            {
                order: "date_to ASC, date_from ASC",
                specification: {
                    work_entry_type_id: { fields: { display_name: {}, color: {} } },
                    date_from: {},
                    date_to: {},
                    type_request_unit: {},
                    accrual_plan_id: { fields: { display_name: {} } },
                    max_leaves: {},
                    virtual_remaining_leaves: {},
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
            const format =
                alloc.type_request_unit === "hour"
                    ? (value) => formatFloatTime(value)
                    : (value) => Number(value.toFixed(2));
            alloc.max_leaves_display = format(alloc.max_leaves);
            alloc.virtual_remaining_leaves_display = format(alloc.virtual_remaining_leaves);
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
