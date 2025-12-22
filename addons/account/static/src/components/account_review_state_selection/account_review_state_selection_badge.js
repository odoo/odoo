import { registry } from "@web/core/registry";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { Component, onWillStart } from "@odoo/owl";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { cookie } from "@web/core/browser/cookie";
import { user } from "@web/core/user";

export class AccountReviewStateSelectionBadge extends Component {
    static template = "account_reports.AccountReviewStateSelectionBadgeField";
    static props = {
        ...standardFieldProps,
        decorations: { type: Object, optional: true },
        options: { type: Object, optional: true },
        class: { type: String, optional: true },
        size: { type: String, optional: true },
    };

    setup() {
        onWillStart(async () => {
            this.editableOptions = await this.getEditableOptions();
        });
    }

    static defaultProps = {
        size: "normal"
    };

    static components = {
        Dropdown,
        DropdownItem,
    }

    get options() {
        return this.props.record.fields[this.props.name].selection;
    }

    get value() {
        return this.props.record.data[this.props.name];
    }

    get required() {
        return this.props.record.fields[this.props.name].required;
    }

    get display() {
        const result = this.options.filter((val) => val[0] === this.value)[0];
        if(result) {
            return result[1];
        }
        return null;
    }

    async getEditableOptions () {
        const editableOptions = []
        if (this.props.options[false] === undefined) {
            editableOptions.push(false);
        }

        for (let [key, value] of Object.entries(this.props.options)) {
            if (
                [true, undefined].includes(value.can_edit)
                || (typeof value.can_edit == 'string' && (await Promise.all(
                    value.can_edit.split(",").map(group => user.hasGroup(group))
                )).some(Boolean))
            ) {
                editableOptions.push(key === 'false' ? false : key);
            }
        }

        return editableOptions;
    }

    getDropdownButtonDecoration(value) {
        const decoration = this.props.options[value]?.decoration
        if (!decoration || decoration === 'muted') {
            return 'btn-outline-secondary'
        }
        return `btn-outline-${decoration}`
    }

    getDropdownItemDecoration(value) {
        const colorScheme = cookie.get("color_scheme");
        const decoration = this.props.options[value]?.decoration;
        if (decoration) {
            if (decoration === "muted") {
                return colorScheme === 'dark' ? "text-bg-200" : "text-bg-300";
            }
            return `text-bg-${decoration}`;
        }
        return "text-bg-200";
    }

    get additionalClassName() {
        const addClasses = [];
        if (this.props.size === 'small' || this.env.config.viewType === 'list') {
            addClasses.push('o_account_review_state_selection_badge_button_small');
        }
        if (this.props.class) {
            addClasses.push(this.props.class);
        }
        return addClasses.join(' ');
    }

    async onChange(value) {
        await this.props.record.update(
            { [this.props.name]: value },
            { save: true }
        );
        this.env.reload?.()
    }
}

export const accountReviewStateSelectionBadge = {
    supportedTypes: ["selection"],
    component: AccountReviewStateSelectionBadge,
    extractProps: ({options}) => {
        return { options };
    },
}

registry.category("fields").add("account_review_state_selection_badge", accountReviewStateSelectionBadge)
