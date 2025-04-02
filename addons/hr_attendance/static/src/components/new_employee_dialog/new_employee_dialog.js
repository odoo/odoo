import { Component, useState, onWillStart } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { rpc } from "@web/core/network/rpc";
import { Dialog } from "@web/core/dialog/dialog";

export class NewEmployeeDialog extends Component {
    static components = { Dialog };
    static props = {
        title: { type: String, optional: true },
        footer: { type: Boolean, optional: true },
        token: { type: String },
    }
    static defaultProps = {
        title: _t("New Set-up"),
        footer: false,
    };
    setup() {
        this.dialogService = useService("dialog");
        this.notification = useService("notification");
        this.state = useState({
            name: "",
            badge: "",
            selectedEmployee: null,
            noBadgeEmployees: [],
        });
        onWillStart(async () => {
            await this.loadEmployeesWithoutBadge();
        });
    }

    async loadEmployeesWithoutBadge() {
        try {
            const data = await rpc('/hr_attendance/get_employees_without_badge', {'token': this.props.token});
            if (!data || data.status !== "success") {
                throw new Error(_t(data?.message || "Failed to load employees"));
            }
            this.state.noBadgeEmployees = data.employees;
        } catch (error) {
            this.notification.add(_t("Error fetching employees: ") + error.message, {
                title: _t("Error"),
                type: "danger",
            });
        }
    }

    async onCreate() {
        try {
            const data = await rpc('/hr_attendance/create_employee', {
                'name': this.state.name,
                'token': this.props.token
            });
            if (data?.status === "success") {
                this.notification.add(_t("Employee created successfully!"), { type: "success",});
                this.props.close();
            } else {
                throw new Error(_t(data?.message || "Unknown error"));
            }
        } catch (error) {
            this.notification.add(_t("Error creating employee: ") + error.message, {
                    title: _t("Error"),
                    type: "danger",
                });
        }
    }

    async onSetBadge() {
        const employeeId = parseInt(this.state.selectedEmployee);
        const badge = this.state.badge?.trim();

        if (!employeeId || !badge) {
            this.notification.add(_t("Please select an employee and enter a badge number."), {
                title: _t("Missing Data"),
                type: "warning",
            });
            return;
        }
        const data = await rpc('/hr_attendance/set_badge', {
            'employee_id': employeeId,
            'badge': badge,
            'token': this.props.token
        });
        if (data?.status === "success") {
            this.notification.add(_t("Badge assigned successfully!"), {
                type: "success",
            });
            this.props.close();
        } else {
            this.notification.add( _t("Error: ") + _t(data?.message || "Something went wrong"),{
                    type: "danger",
                    title: _t("Error"),
                });
        }
    }

    static template = "hr_attendance.NewEmployeeDialog";
}
