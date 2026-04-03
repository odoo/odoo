import { Component } from "@odoo/owl";
import { standardFieldProps } from "../standard_field_props";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { hasTouch } from "@web/core/browser/feature_detection";

const DROPDOWN_ITEM_LIMIT = 8;
export class BaseBadgesField extends Component {
    static template = "web.BaseBadgesField";
    static props = {
        ...standardFieldProps,
        badgeLimit: { type: Number, optional: true },
        options: { type: Array },
        string: { type: String },
        value: [String, Number, Boolean, { value: null }],
        onChange: { type: Function },
        canDeselect: { type: Boolean, optional: true },
        onSearchMore: { type: Function, optional: true },
    };
    static components = {
        Dropdown,
        DropdownItem,
    };

    /**
     * Computes the ordered list of options. If the selected value is
     * beyond the limit, it is moved into the visible "unfolded" range.
     */
    get optionsDict() {
        const { options, badgeLimit, value } = this.props;
        const displayOptions = [...options];

        if (this.hasMoreThanMax) {
            const index = displayOptions.findIndex((opt) => opt[0] === value);

            // If selected value is in the "More" dropdown, move it to the visible limit
            if (index >= badgeLimit) {
                const [selectedOption] = displayOptions.splice(index, 1);
                displayOptions.splice(badgeLimit - 1, 0, selectedOption);
            }
        }

        return {
            unfolded: badgeLimit ? displayOptions.slice(0, badgeLimit) : displayOptions,
            folded: badgeLimit ? displayOptions.slice(badgeLimit) : [],
        };
    }

    get badgesOptions() {
        return this.optionsDict.unfolded;
    }

    get dropdownOptions() {
        if (!this.hasMoreThanMax) {
            return [];
        }

        const { onSearchMore } = this.props;
        const { folded } = this.optionsDict;
        return onSearchMore ? folded.slice(0, DROPDOWN_ITEM_LIMIT) : folded;
    }

    get extraBadgeLabel() {
        const hiddenCount = this.props.options.length - this.props.badgeLimit;
        return `+${hiddenCount}`;
    }

    get hasMoreThanMax() {
        return this.props.badgeLimit && this.props.options.length > this.props.badgeLimit;
    }

    get string() {
        return this.props.string;
    }

    get value() {
        return this.props.value;
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
