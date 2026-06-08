import { Component, props, proxy, t } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { rpc } from "@web/core/network/rpc";
import { Dialog } from "@web/core/dialog/dialog";
import { Many2One } from "./many2one/many2one";

export class NewEmployeeDialog extends Component {
    static components = { Dialog, Many2One };
    static template = "hr_attendance.NewEmployeeDialog";
    props = props({
        title: t.string().optional(_t("Badge Set-up")),
        footer: t.boolean().optional(false),
        token: t.string(),
    });
    setup() {
        this.dialogService = useService("dialog");
        this.notification = useService("notification");
        this.state = proxy({
            employeeName: "",
            badgeId: "",
            value: null,
            searchName: "",
            employeeHasBadge: false,
        });
    }

    onSelectEmployee(emp) {
        this.state.searchName = emp?.name ?? "";
        this.state.badgeId = "";
        if(emp?.isNew){
            this.state.searchName = emp.name;
            this.state.employeeName = emp.name;
            this.state.value = null;
            this.state.employeeHasBadge = false;
            this.onCreate();
        }
        else if(this.state.searchName == ""){
            this.state.value = null;
        } else {
            this.state.value = emp;
            this.state.employeeHasBadge = false;
        }
    }

    async onCreate() {
        if (!this.state.employeeName || this.state.employeeName.trim() === "") {
            this.notification.add(_t("Employee name is required."), {
                title: _t("Validation Error"),
                type: "warning",
            });
            return;
        }
        try {
            const result = await rpc("/hr_attendance/create_employee", {
                name: this.state.employeeName,
                token: this.props.token,
            });
            const is_created = result.status;
            const created_emp = result.employee;
            if (is_created) {
                this.notification.add(_t("Employee created successfully!"), {type: "success"});
                this.state.value = created_emp
            } else {
                this.notification.add(_t("Failed to create employee."), {
                    type: "danger",
                });
            }
        } catch (error) {
            this.notification.add(_t("Error creating employee: ") + error.message, {
                type: "danger",
            });
        }
    }

    async onSetBadge() {
        const badge = this.state.badgeId?.trim();
        if (!this.state.value || !badge) {
            this.notification.add(_t("Please select an employee and enter a badge number."), {
                title: _t("Missing Data"),
                type: "warning",
            });
            return;
        }
        const employeeId = parseInt(this.state.value.id);
        const data = await rpc("/hr_attendance/set_badge", {
            employee_id: employeeId,
            badge: badge,
            token: this.props.token,
        });
        if (data?.status === "success") {
            this.notification.add(_t("Badge assigned successfully!"), {
                type: "success",
            });
            this.state.employeeHasBadge = true;
        } else {
            this.notification.add(_t("Error: ") + _t(data?.message), {
                type: "danger",
            });
        }
    }
}
