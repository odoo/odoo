import { registry } from "@web/core/registry";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { Component, onWillStart, props, t } from "@odoo/owl";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { cookie } from "@web/core/browser/cookie";
import { user } from "@web/core/user";


export class AccountReviewStateSelectionBadge extends Component {
    static template = "account_reports.AccountReviewStateSelectionBadgeField";
    props = props({
        ...standardFieldProps,
        decorations: t.object().optional(),
        options: t.object().optional(),
        class: t.string().optional(),
        size: t.string().optional("normal"),
        onChange: t.function().optional(),
    });

    setup() {
        this.selection_map = new Map(this.props.record.fields[this.props.name].selection);

        onWillStart(async () => {
            this.editableOptions = await this.getEditableOptions();
        });
    }

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
        const value = this.value;
        if (this.selection_map.has(value)) {
            return this.selection_map.get(value);
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

    getIcon(value) {
        return this.props.options[value]?.icon;
    }

    getDropdownButtonFill(value) {
        return this.props.options[value]?.fill;
    }

    getDropdownButtonDecoration(value) {
        const decoration = this.props.options[value]?.decoration
        const fill = this.getDropdownButtonFill(value) ? "btn" : "btn-outline";
        if (!decoration || decoration === 'muted') {
            return `${fill}-secondary`
        }
        return `${fill}-${decoration}`
    }

    getDropdownItemDecoration(value, hasIcon = false) {
        const colorScheme = cookie.get("color_scheme");
        const decoration = this.props.options[value]?.decoration;
        const decorationClassName = hasIcon ? "text" : "text-bg";
        if (decoration) {
            if (decoration === "muted") {
                return colorScheme === 'dark' ? `${decorationClassName}-200` : `${decorationClassName}-300`;
            }
            return `${decorationClassName}-${decoration}`;
        }
        return `${decorationClassName}-200`;
    }

    get additionalClassName() {
        const addClasses = [];
        if (this.props.size === 'small' || this.env.config?.viewType === 'list') {
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
        if (this.props.onChange) {
            await this.props.onChange(value);
        }
        this.env.reload?.()
    }
}

export const accountReviewStateSelectionBadge = {
    supportedTypes: ["selection"],
    component: AccountReviewStateSelectionBadge,
    extractProps: ({options}) => ({ options }),
}

registry.category("fields").add("account_review_state_selection_badge", accountReviewStateSelectionBadge)
