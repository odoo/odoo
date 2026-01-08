/** @odoo-module **/

import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { standardFieldProps } from "../standard_field_props";

import { Component } from "@odoo/owl";

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
};

registry.category("fields").add("handle", handleField);
