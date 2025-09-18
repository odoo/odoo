// @ts-check

/** @module @web/fields/selection/selection/selection_field - Standard dropdown selection field for Selection and Many2one columns */

import { SelectMenu } from "@web/components/select_menu/select_menu";
import { hasTouch } from "@web/core/browser/feature_detection";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { SelectionLikeField } from "@web/fields/selection/selection_like_field";
import { standardFieldProps } from "@web/fields/standard_field_props";

export class SelectionField extends SelectionLikeField {
    static components = {
        SelectMenu,
    };
    static template = "web.SelectionField";
    static props = {
        ...standardFieldProps,
        placeholder: { type: String, optional: true },
        required: { type: Boolean, optional: true },
        domain: { type: [Array, Function], optional: true },
        autosave: { type: Boolean, optional: true },
    };
    static defaultProps = {
        autosave: false,
    };

    get choices() {
        return this.options.map(([value, label]) => ({ value, label }));
    }
    get isBottomSheet() {
        return this.env.isSmall && hasTouch();
    }
    get options() {
        switch (this.type) {
            case "many2one":
                return [...this.specialData.data];
            case "selection":
                return this.props.record.fields[this.props.name].selection.filter(
                    (option) => option[1] !== "",
                );
            default:
                return [];
        }
    }

    onChange(value) {
        switch (this.type) {
            case "many2one":
                if (value === null) {
                    this.props.record.update(
                        { [this.props.name]: false },
                        { save: this.props.autosave },
                    );
                } else {
                    const option = this.options.find((option) => option[0] === value);
                    this.props.record.update(
                        {
                            [this.props.name]: {
                                id: option[0],
                                display_name: option[1],
                            },
                        },
                        { save: this.props.autosave },
                    );
                }
                break;
            case "selection":
                this.props.record.update(
                    { [this.props.name]: value ?? false },
                    { save: this.props.autosave },
                );
                break;
        }
    }
}

export const selectionField = {
    component: SelectionField,
    displayName: _t("Selection"),
    supportedOptions: [
        {
            label: _t("Dynamic Placeholder"),
            name: "placeholder_field",
            type: "field",
            availableTypes: ["char"],
        },
    ],
    supportedTypes: ["many2one", "selection"],
    isEmpty: (record, fieldName) => record.data[fieldName] === false,
    extractProps({ viewType, placeholder }, dynamicInfo) {
        const props = {
            autosave: viewType === "kanban",
            placeholder,
            required: dynamicInfo.required,
            domain: dynamicInfo.domain,
        };
        if (viewType === "kanban") {
            props.readonly = dynamicInfo.readonly;
        }
        return props;
    },
};

registry.category("fields").add("selection", /** @type {any} */ (selectionField));
