// @ts-check

/** @module @web/fields/display/handle/handle_field - Drag handle icon for manual record reordering in list views */

import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/fields/standard_field_props";

export class HandleField extends Component {
    static template = "web.HandleField";
    static props = {
        ...standardFieldProps,
    };
}

export const handleField = {
    component: HandleField,
    displayName: _t("Handle"),
    supportedTypes: ["integer"],
    isEmpty: () => false,
    listViewWidth: 20,
    extractProps(_, dynamicInfo) {
        return {
            readonly: dynamicInfo.readonly,
        };
    },
};

registry.category("fields").add("handle", handleField);
