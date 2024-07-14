/** @odoo-module */

import { _t } from "@web/core/l10n/translation";

/**
 * This object describes the properties editable in studio, depending on
 * one or more attribute of a field. The TypeWidgetProperties component will
 * retrieve the value by itself, or you can set a function with the `getValue`
 * key to compute it specifically for one editable property.
 */
export const EDITABLE_ATTRIBUTES = {
    context: {
        name: "context",
        label: _t("Context"),
        type: "string",
    },
    domain: {
        name: "domain",
        label: _t("Domain"),
        type: "domain",
        getValue({ attrs, field }) {
            return {
                domain: attrs.domain,
                relation: field.relation,
            };
        },
    },
    aggregate: {
        name: "aggregate",
        label: _t("Aggregate"),
        type: "selection",
        choices: [
            { value: "sum", label: _t("Sum") },
            { value: "avg", label: _t("Average") },
            { value: "none", label: _t("No aggregation") },
        ],
        getValue({ attrs }) {
            return attrs.sum ? "sum" : attrs.avg ? "avg" : "none";
        },
    },
    placeholder: {
        name: "placeholder",
        label: _t("Placeholder"),
        type: "string",
    },
};

export const FIELD_TYPE_ATTRIBUTES = {
    char: {
        common: [EDITABLE_ATTRIBUTES.placeholder],
    },
    date: {
        common: [EDITABLE_ATTRIBUTES.placeholder],
    },
    datetime: {
        common: [EDITABLE_ATTRIBUTES.placeholder],
    },
    float: {
        common: [EDITABLE_ATTRIBUTES.placeholder],
        list: [EDITABLE_ATTRIBUTES.aggregate],
    },
    html: {
        common: [EDITABLE_ATTRIBUTES.placeholder],
    },
    integer: {
        common: [EDITABLE_ATTRIBUTES.placeholder],
        list: [EDITABLE_ATTRIBUTES.aggregate],
    },
    many2many: {
        common: [EDITABLE_ATTRIBUTES.domain, EDITABLE_ATTRIBUTES.context],
    },
    many2one: {
        common: [
            EDITABLE_ATTRIBUTES.domain,
            EDITABLE_ATTRIBUTES.context,
            EDITABLE_ATTRIBUTES.placeholder,
        ],
    },
    monetary: {
        common: [EDITABLE_ATTRIBUTES.placeholder],
        list: [EDITABLE_ATTRIBUTES.aggregate],
    },
    selection: {
        common: [EDITABLE_ATTRIBUTES.placeholder],
    },
};

/**
 * Computed Options are options that are tied to another option.
 * Their value and visibility depends on another option present in the sidebar.
 *
 * They must be documented using 'supportedOptions' on any field widget.
 * Then, register them under COMPUTED_DISPLAY_OPTIONS using the technical name of the option.
 *
 * Here is how to declare them :
 *
 *      COMPUTED_DISPLAY_OPTIONS = {
 *          dependent_option: {
 *              superOption (string): technical name of another option that has an impact on the dependent option.
 *                                      This option must also be documented under 'supportedOptions'.
 *              getValue (function): compute the value of the dependent option from super option value
 *              getReadonly (function): compute a boolean based on the super value.
 *                                      If true, the option is greyed out and it is not possible to interact with them.
 *                                      Otherwise, the dependent option can still be edited.
 *              getInvisible (function): compute a boolean based on the super value.
 *                                      If true, the option is not present in the sidebar.
 *          },
 *          ...
 *      }
 *
 */

export const COMPUTED_DISPLAY_OPTIONS = {
    collaborative_trigger: {
        superOption: "collaborative",
        getInvisible: (value) => !value,
    },
    no_quick_create: {
        superOption: "no_create",
        getValue: (value) => value,
        getReadonly: (value) => value,
    },
    no_create_edit: {
        superOption: "no_create",
        getValue: (value) => value,
        getReadonly: (value) => value,
    },
    decimals: {
        superOption: "human_readable",
        getInvisible: (value) => !value,
    },
    zoom_delay: {
        superOption: "zoom",
        getInvisible: (value) => !value,
    },
    dynamic_placeholder_model_reference_field: {
        superOption: "dynamic_placeholder",
        getInvisible: (value) => !value,
    },
    edit_max_value: {
        superOption: "editable",
        getInvisible: (value) => !value,
    },
    no_edit_color: {
        superOption: "color_field",
        getInvisible: (value) => !value,
    },
};
