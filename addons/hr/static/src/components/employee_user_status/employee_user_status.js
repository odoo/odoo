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
    false: { label: _t("Not Invited"), decoration: "danger", icon: "person_off" },
    new: { label: _t("Invited"), decoration: "warning", icon: "send" },
    active: { label: _t("Confirmed"), decoration: "success", icon: "check_circle" },
    inactive: { label: _t("Archived"), decoration: "danger", icon: "block" },
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
        return STATUS[this.state] || {};
    }

    get buttonClass() {
        return `btn-outline-${this.status.decoration || 'secondary'}`;
    }

    get icon() {
        return STATUS[this.state]['icon'];
    }

    get items() {
        switch (this.state) {
            case "new":
                return [
                    { key: "send", label: _t("Resend Invitation"), icon: "send", method: "action_send_invitation" },
                    { key: "copy", label: _t("Copy Invitation Link"), icon: "content_copy", method: "action_copy_invitation_link" },
                    { key: "deactivate", label: _t("Deactivate"), icon: "block", method: "action_toggle_user_active" },
                ];
            case "active":
                return [
                    { key: "reset", label: _t("Reset Password"), icon: "key", method: "action_reset_password" },
                    { key: "deactivate", label: _t("Deactivate"), icon: "block", method: "action_toggle_user_active" },
                ];
            case "inactive":
                return [
                    { key: "reactivate", label: _t("Reactivate"), icon: "lock_open_right", method: "action_toggle_user_active" },
                ];
            default:
                return [
                    { key: "create_user", label: _t("Invite"), icon: "person_add", method: "action_send_invitation" },
                ];
        }
    }

    async onSelect(item) {
        await this.props.record.save();
        const resId = this.props.record.resId;
        if (!resId) {
            return;
        }
        const result = await this.orm.call("hr.employee", item.method, [resId]);
        if (item.key === 'create_user') {
            await this.action.doAction(result); // will soft reload.
        } else if (result && item.key === 'copy') {
            await browser.navigator.clipboard.writeText(result);
            this.notification.add(_t("Invitation link copied to clipboard."), { type: "success" });
        } else if (result && typeof result === "object") {
            await this.action.doAction(result, { onClose: () => this.props.record.load() });
        } else {
            await this.props.record.load();
        }
    }
}

export const employeeUserStatus = {
    component: EmployeeUserStatus,
    supportedTypes: ["selection"],
};

registry.category("fields").add("employee_user_status", employeeUserStatus);
