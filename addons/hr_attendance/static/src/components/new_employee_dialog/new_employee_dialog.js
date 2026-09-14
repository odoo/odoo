/** @odoo-module native */
import { Component, useState } from "@odoo/owl";
import { _t } from "@web/core/translation";
import { useService } from "@web/core/utils/hooks";
import { rpc } from "@web/core/network";
import { Dialog } from "@web/ui/dialog";
import { Many2One } from "./many2one/many2one.js";

export class NewEmployeeDialog extends Component {
    static components = { Dialog, Many2One };
    static template = "hr_attendance.NewEmployeeDialog";
    static props = {
        title: { type: String, optional: true },
        footer: { type: Boolean, optional: true },
        token: { type: String },
    };
    static defaultProps = {
        title: _t("Set-up"),
        footer: false,
    };
    setup() {
        this.dialogService = useService("dialog");
        this.notification = useService("notification");
        this.state = useState({
            employeeName: "",
            badgeId: "",
            value: null,
            searchName: "",
        });
    }

    onSelectEmployee(emp) {
        this.state.searchName = emp?.name ?? "";
        if (this.state.searchName == "") {
            this.state.value = null;
        } else {
            this.state.value = emp;
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
            // The route answers `{status}` like the rest of the kiosk surface.
            // It used to answer `true`/`false`, and the falsy branch below was
            // the only thing telling the setup session that its own refusal --
            // an AccessError the route did not catch -- had happened at all.
            const result = await rpc("/hr_attendance/create_employee", {
                name: this.state.employeeName,
                token: this.props.token,
            });
            if (result?.status === "success") {
                this.notification.add(_t("Employee created successfully!"), {
                    type: "success",
                });
                this.props.close();
            } else {
                this.notification.add(
                    result?.message ?? _t("Failed to create employee."),
                    { type: "danger" },
                );
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
            this.notification.add(
                _t("Please select an employee and enter a badge number."),
                {
                    title: _t("Missing Data"),
                    type: "warning",
                },
            );
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
            this.props.close();
        } else {
            this.notification.add(_t("Error: ") + data?.message, {
                type: "danger",
            });
        }
    }
}
