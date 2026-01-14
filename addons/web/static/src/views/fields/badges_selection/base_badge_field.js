import { Component } from "@odoo/owl";
import { SelectMenu } from "@web/core/select_menu/select_menu";
import { hasTouch } from "@web/core/browser/feature_detection";
import { standardFieldProps } from "../standard_field_props";

export class BaseBadgeField extends Component {
    static template = "web.BaseBadgeField";
    static props = {
        ...standardFieldProps,
        badgeLimit: { type: Number, optional: true },
        placeholder: { type: String, optional: true },
        options: { type: Array },
        string: { type: String },
        value: [String, Number, Boolean],
        onChange: { type: Function },
        canDeselect: { type: Boolean, optional: true },
    };
    static components = {
        SelectMenu,
    };

    get options() {
        return this.props.options;
    }

    get string() {
        return this.props.string;
    }

    get value() {
        return this.props.value;
    }

    get hasMoreThanMax() {
        return this.props.badgeLimit && this.options.length > this.props.badgeLimit;
    }

    get selectOptions() {
        return this.options.map(([value, label, icon]) => ({ value, label, icon }));
    }

    get isBottomSheet() {
        return this.env.isSmall && hasTouch();
    }

    stringify(value) {
        return JSON.stringify(value);
    }

    onChange(value) {
        if (value === this.value && this.props.canDeselect) {
            this.props.onChange(false);
        } else {
            this.props.onChange(value);
        }
    }

    getBadgeClassNames(option = false) {
        return this.props.readonly ? "" : { active: this.value === option[0] };
    }
}

export const extractStandardFieldProps = (props = {}) => ({
    id: props.id,
    name: props.name,
    readonly: props.readonly,
    record: props.record,
});
