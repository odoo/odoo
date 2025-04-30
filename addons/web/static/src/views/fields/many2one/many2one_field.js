import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { computeM2OProps, Many2One } from "./many2one";
import { standardFieldProps } from "../standard_field_props";
import { evaluateBooleanExpr } from "@web/core/py_js/py";

/** @type {import("registries").FieldsRegistryItemShape["supportedOptions"]} */
export const m2oSupportedOptions = [
    {
        label: _t("Disable opening"),
        name: "no_open",
        type: "boolean",
    },
    {
        label: _t("Disable creation"),
        name: "no_create",
        type: "boolean",
        help: _t(
            "If checked, users won't be able to create records through the autocomplete dropdown at all."
        ),
    },
    {
        label: _t("Disable 'Create' option"),
        name: "no_quick_create",
        type: "boolean",
        help: _t(
            "If checked, users will not be able to create records based on the text input; they will still be able to create records via a popup form."
        ),
    },
    {
        label: _t("Disable 'Create and Edit' option"),
        name: "no_create_edit",
        type: "boolean",
        help: _t(
            "If checked, users will not be able to create records based through a popup form; they will still be able to create records based on the text input."
        ),
    },
    {
        label: _t("Typeahead search"),
        name: "search_threshold",
        type: "number",
        help: _t(
            "Defines the minimum number of characters to perform the search. If not set, the search is performed on focus."
        ),
    },
    {
        label: _t("Dynamic placeholder"),
        name: "placeholder_field",
        type: "field",
        availableTypes: ["char"],
    },
];
/** @type {import("registries").FieldsRegistryItemShape["supportedTypes"]} */
export const m2oSupportedTypes = ["many2one"];

/**
 * @param {typeof Component} component
 * @returns {import("registries").FieldsRegistryItemShape}
 */
export function buildM2OFieldDescription(component) {
    return {
        component,
        displayName: _t("Many2one"),
        extractProps: extractM2OFieldProps,
        supportedOptions: m2oSupportedOptions,
        supportedTypes: m2oSupportedTypes,
    };
}

export function extractM2OFieldProps(staticInfo, dynamicInfo) {
    const { attrs, context, decorations, options, string, placeholder } = staticInfo;

    const hasCreatePermission = attrs.can_create ? evaluateBooleanExpr(attrs.can_create) : true;
    const hasWritePermission = attrs.can_write ? evaluateBooleanExpr(attrs.can_write) : true;
    const canCreate = options.no_create ? false : hasCreatePermission;
    return {
        canCreate,
        canCreateEdit: canCreate && !options.no_create_edit,
        canOpen: !options.no_open,
        canQuickCreate: canCreate && !options.no_quick_create,
        canScanBarcode: !!options.can_scan_barcode,
        canWrite: hasWritePermission,
        context: dynamicInfo.context,
        decorations,
        domain: dynamicInfo.domain,
        nameCreateField: options.create_name_field,
        openActionContext: context || "{}",
        placeholder,
        searchThreshold: options.search_threshold,
        string,
    };
}

export class Many2OneField extends Component {
    static template = "web.Many2OneField";
    static components = { Many2One };
    static props = {
        ...standardFieldProps,
        canCreate: { type: Boolean, optional: true },
        canCreateEdit: { type: Boolean, optional: true },
        canOpen: { type: Boolean, optional: true },
        canQuickCreate: { type: Boolean, optional: true },
        canScanBarcode: { type: Boolean, optional: true },
        canWrite: { type: Boolean, optional: true },
        context: { type: Object, optional: true },
        decorations: { type: Object, optional: true },
        domain: { type: [Array, Function], optional: true },
        nameCreateField: { type: String, optional: true },
        openActionContext: { type: String, optional: true },
        placeholder: { type: String, optional: true },
        searchLimit: { type: Number, optional: true },
        searchThreshold: { type: Number, optional: true },
        string: { type: String, optional: true },
    };

    get m2oProps() {
        return computeM2OProps(this.props);
    }
}

registry.category("fields").add("many2one", {
    ...buildM2OFieldDescription(Many2OneField),
});
