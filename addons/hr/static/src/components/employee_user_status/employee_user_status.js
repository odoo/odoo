import { registry } from "@web/core/registry";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { Component } from "@odoo/owl";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { useService } from "@web/core/utils/hooks";
import { browser } from "@web/core/browser/browser";
import { _t } from "@web/core/l10n/translation";

// Visual representation of res.users.state, mirrored on the employee.
const STATUS = {
    new: { label: _t("Invited"), decoration: "warning", icon: "fa-paper-plane" },
    active: { label: _t("Confirmed"), decoration: "success", icon: "fa-check-circle" },
    inactive: { label: _t("Archived"), decoration: "danger", icon: "fa-ban" },
};

/**
 * Header widget on the employee form showing the linked user's invitation /
 * activation status as a pill, with a state-dependent menu of actions. Each
 * action is a method on hr.employee (no client-side state writes).
 */
export class EmployeeUserStatus extends Component {
    static template = "hr.EmployeeUserStatus";
    static components = { Dropdown, DropdownItem };
    static props = { ...standardFieldProps };

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.action = useService("action");
    }

    get state() {
        return this.props.record.data[this.props.name];
    }

    get status() {
        return STATUS[this.state] || null;
    }

    get buttonClass() {
        return this.status ? `btn-outline-${this.status.decoration}` : "btn-outline-secondary";
    }

    get items() {
        switch (this.state) {
            case "new":
                return [
                    { key: "send", label: _t("Resend Invitation"), icon: "fa-paper-plane", method: "action_send_invitation" },
                    { key: "copy", label: _t("Copy Invitation Link"), icon: "fa-clipboard", method: "action_copy_invitation_link", copy: true },
                    { key: "deactivate", label: _t("Deactivate"), icon: "fa-ban", method: "action_toggle_user_active" },
                ];
            case "active":
                return [
                    { key: "reset", label: _t("Reset Password"), icon: "fa-key", method: "action_reset_password" },
                    { key: "deactivate", label: _t("Deactivate"), icon: "fa-ban", method: "action_toggle_user_active" },
                ];
            case "inactive":
                return [
                    { key: "reactivate", label: _t("Reactivate"), icon: "fa-unlock", method: "action_toggle_user_active" },
                ];
            default:
                return [];
        }
    }

    async onSelect(item) {
        const resId = this.props.record.resId;
        if (!resId) {
            return;
        }
        const result = await this.orm.call("hr.employee", item.method, [resId]);
        if (item.copy) {
            if (result) {
                await browser.navigator.clipboard.writeText(result);
                this.notification.add(_t("Invitation link copied to clipboard."), { type: "success" });
            }
            return;
        }
        if (result && typeof result === "object") {
            await this.action.doAction(result);
        }
        await this.props.record.load();
    }
}

export const employeeUserStatus = {
    component: EmployeeUserStatus,
    supportedTypes: ["selection"],
};

registry.category("fields").add("employee_user_status", employeeUserStatus);
