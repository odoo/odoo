import { registry } from "@web/core/registry";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { Component, onWillStart } from "@odoo/owl";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { cookie } from "@web/core/browser/cookie";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

export class EmployeeUserStatus extends Component {
    static template = "hr.EmployeeUserStatus";
    static props = {
        ...standardFieldProps,
        options: { type: Object, optional: true },
        showSelectedIcon: { type: String, optional: true },
        highlightChatter: { type: Boolean, optional: true },
    };

    setup() {
        this.actionService = useService("action");
        this.orm = useService("orm");
        this.notification = useService("notification");
        onWillStart(async () => {
            this.editableOptions = await this.getEditableOptions();
        });
    }

    static components = {
        Dropdown,
        DropdownItem,
    };

    get options() {
        let options = [];
        var self = this;
        let selection = this.props.record.fields[this.props.name].selection;
        selection = Object.assign({}, ...selection.map((item) => ({[item[0]]: item[1]})));
        Object.keys(this.props.options).forEach(function(key) {
           options.push([key, self.props.options[key]['text'] || selection[key]]);
        });
        return options;
    }

    get value() {
        return this.props.record.data[this.props.name];
    }

    get display() {
        const result = this.options.filter((val) => val[0] === this.value)[0];
        if(result) {
            return this.props.options[result[0]]?.text ? this.props.options[result[0]].text : result[1];
        }
        return null;
    }

    get showIcon() {
        const result = this.options.filter((val) => val[0] === this.value)[0];
        return this.props.showSelectedIcon && result
    }

    async getEditableOptions() {
        const editableOptions = [];
        for (const [key, value] of Object.entries(this.props.options)) {
            if (value.display === true || this.props.record.data[value.display]
                || (this.props.record.data["user_state"] === 'new' && (['action_resend', 'action_copy', 'deactivate'].includes(key)))
                || (this.props.record.data["user_state"] === 'active' && (['action_reset_password', 'deactivate'].includes(key)))
                || (this.props.record.data["user_state"] === 'inactive' && (['action_send', 'reactivate'].includes(key)))
            ) {
                editableOptions.push(key);
            }
        }

        return editableOptions;
    }

    get canEditAny() {
        return this.editableOptions.length > 0;
    }

    getDropdownButtonDecoration(value) {
        const decoration = this.props.options[value]?.decoration;
        if (!decoration || decoration === 'muted') {
            return 'btn-outline-secondary';
        }
        return `btn-outline-${decoration}`;
    }

    getDropdownItemDecoration(value) {
        const colorScheme = cookie.get("color_scheme");
        const decoration = this.props.options[value]?.decoration;
        const icon = this.props.options[value]?.icon;
        const decorationClassName = icon ? 'text' : 'text-bg';
        if (decoration) {
            if (decoration === "muted") {
                return colorScheme === 'dark' ? "text-200" : "text-300";
            }
            return `${decorationClassName}-${decoration}`;
        }
        return `${decorationClassName}-200`;
    }

    getIcon(value) {
        return this.props.options[value]?.icon || "fa fa-circle";
    }

    async onChange(value) {
        const action = this.props.options[value]['action'];
        if (!action) {
            await this.props.record.update(
                {[this.props.name]: value},
                {save: true},
            );
        } else {
            await this[action](value);
        }
        this.editableOptions = await this.getEditableOptions();
    }

    async deactivate(value) {
        await this.orm.write('res.users', [this.props.record.data['user_id'].id], {'active': false});
        await this.props.record.load();
        if (this.props.record.data['is_in_contract']) {
            const action = await this.orm.call('hr.employee', 'action_new_departure', [this.props.record.data['id']], {});
            return this.actionService.doAction(action);
        }
    }

    async reactivate(){
        await this.orm.write('res.users', [this.props.record.data['user_id'].id], {'active': true});
        await this.props.record.load();
    }

    sendInvitation() {
        alert('Send Invitation');
    }

    async copyInvitationLink() {
        // navigator.clipboard.writeText(this.props.record.data['user_id'].invitationLink);
        navigator.clipboard.writeText('https://www.zatorband.com');
        this.notification.add(_t("Invitation link copied"), { type: "success" });
    }

    async resetPassword() {
        const action = await this.orm.call('res.users', 'action_change_password_wizard', [this.props.record.data['user_id'].id], {});
        return this.actionService.doAction(action);
    }
}

export const employeeUserStatus = {
    supportedTypes: ["selection"],
    component: EmployeeUserStatus,
    extractProps: ({ attrs, options }) => {
        return {
            options,
            showSelectedIcon: attrs.icon,
            highlightChatter: attrs.highlight_chatter === "1",
        };
    },
};

registry.category("fields").add("employee_user_status", employeeUserStatus);
