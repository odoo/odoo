// @ts-check
/** @odoo-module native */

import { SelectMenu } from "@web/components/select_menu/select_menu";
import { hasTouch } from "@web/core/browser/feature_detection";
import { _t } from "@web/core/translation";
import { registerField } from "@web/fields/_registry";
import { placeholderFieldOption } from "@web/fields/field_options";
import { isFalseEmpty } from "@web/fields/field_utils";
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
        context: { type: Object, optional: true },
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
    onChange(value) {
        if (!this.isReady || this.props.readonly) {
            return;
        }
        const options = { save: this.props.autosave };
        switch (this.type) {
            case "many2one": {
                const next = this.many2oneValueFor(value, this.options);
                if (next !== undefined) {
                    this.field.update(next, options);
                }
                break;
            }
            case "selection":
                this.field.update(value ?? false, options);
                break;
        }
    }
}

export const selectionField = {
    component: SelectionField,
    displayName: _t("Selection"),
    supportedOptions: [placeholderFieldOption()],
    supportedTypes: ["many2one", "selection"],
    isEmpty: isFalseEmpty,
    interactiveOutsideEdition: ({ viewType }) => viewType === "kanban",
    extractProps({ viewType, placeholder = undefined }, dynamicInfo) {
        return {
            autosave: viewType === "kanban",
            placeholder,
            required: dynamicInfo.required,
            domain: dynamicInfo.domain,
            context: dynamicInfo.context,
        };
    },
};

registerField("selection", /** @type {any} */ (selectionField));
