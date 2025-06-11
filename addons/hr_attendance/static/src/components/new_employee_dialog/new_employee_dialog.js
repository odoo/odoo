import { Component, useState } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { rpc } from "@web/core/network/rpc";
import { Dialog } from "@web/core/dialog/dialog";
import { AutoComplete } from "@web/core/autocomplete/autocomplete";

export class NewEmployeeDialog extends Component {
    static components = { AutoComplete, Dialog };
    static template = "hr_attendance.NewEmployeeDialog";
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
            searchQuery: "",
        });
    }

    get sources() {
        return [{
            options: this.loadOptionsSource.bind(this),
            optionSlot: "option",
        }];
    }

    onSelectEmployee(emp) {
        this.state.selectedEmployee = emp;
        this.state.searchQuery = emp.name;
    }

    clearSelection() {
        this.state.selectedEmployee = null;
    }

    async loadOptionsSource(input) {
        const query = (input || "").trim();
        const data = await rpc('/hr_attendance/get_employees_without_badge', { token: this.props.token , query: query });
        if (data && data.status === "success") {
            this.state.noBadgeEmployees = data.employees;
        }
        if (data && data.status === "success") {
            return data.employees.map(emp => ({
                data: { id: emp.id },
                label: emp.name,
                onSelect: () => this.onSelectEmployee(emp),
            }));
        }

        return [];
    }

    async onCreate() {
        if (!this.state.name || this.state.name.trim() === "") {
            this.notification.add(_t("Employee name is required."), {
                title: _t("Validation Error"),
                type: "warning",
            });
            return;
        }
        try {
            const data = await rpc('/hr_attendance/create_employee', {
                name: this.state.name,
                token: this.props.token
            });
            if (data) {
                this.notification.add(_t("Employee created successfully!"), { type: "success",});
                this.props.close();
            }
        } catch (error) {
            this.notification.add(_t("Error creating employee: ") + error.message, {
                    title: _t("Error"),
                    type: "danger",
                });
        }
    }

    async onSetBadge() {
        const badge = this.state.badge?.trim();
        if (!this.state.selectedEmployee || !badge) {
            this.notification.add(_t("Please select an employee and enter a badge number."), {
                title: _t("Missing Data"),
                type: "warning",
            });
            return;
        }
        const employeeId = parseInt(this.state.selectedEmployee.id);
        const data = await rpc('/hr_attendance/set_badge', {
            employee_id: employeeId,
            badge: badge,
            token: this.props.token
        });
        if (data?.status === "success") {
            this.notification.add(_t("Badge assigned successfully!"), {
                type: "success",
            });
            this.props.close();
        } else {
            this.notification.add( _t("Error: ") + _t(data?.message),{
                type: "danger",
                title: _t("Error"),
            });
        }
    }
}
