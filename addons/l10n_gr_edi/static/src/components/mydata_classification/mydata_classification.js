/** @odoo-module **/

import { registry } from "@web/core/registry";
import { SelectionField, selectionField } from "@web/views/fields/selection/selection_field";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

export class DynamicSelectionField extends SelectionField {

    static props = {
        ...standardFieldProps,
        available_field: {type: String},
    }

    /** To be overridden **/
    get availableOptions() {
        return this.props.record.data[this.props.available_field]?.split(",") || [];
    }

    /** Override **/
    get options() {
        const availableOptions = this.availableOptions;
        return super.options.filter(x => availableOptions.includes(x[0]));
    }

}

registry.category("fields").add("selection_l10n_gr_edi_inv_type", {
    ...selectionField,
    component: DynamicSelectionField,
    extractProps: (fieldInfo, dynamicInfo) => ({
        // ...selectionField.extractProps(fieldInfo, dynamicInfo),
        available_field: "l10n_gr_edi_available_inv_type",
    }),
});
registry.category("fields").add("selection_l10n_gr_edi_cls_category", {
    ...selectionField,
    component: DynamicSelectionField,
    extractProps: (fieldInfo, dynamicInfo) => ({
        // ...selectionField.extractProps(fieldInfo, dynamicInfo),
        available_field: "l10n_gr_edi_available_cls_category",
    }),
});
registry.category("fields").add("selection_l10n_gr_edi_cls_type", {
    ...selectionField,
    component: DynamicSelectionField,
    extractProps: (fieldInfo, dynamicInfo) => ({
        // ...selectionField.extractProps(fieldInfo, dynamicInfo),
        available_field: "l10n_gr_edi_available_cls_type",
    }),
});
registry.category("fields").add("selection_l10n_gr_edi_cls_vat", {
    ...selectionField,
    component: DynamicSelectionField,
    extractProps: (fieldInfo, dynamicInfo) => ({
        // ...selectionField.extractProps(fieldInfo, dynamicInfo),
        available_field: "l10n_gr_edi_available_cls_vat",
    }),
});
