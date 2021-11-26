/** @odoo-module **/

import { registry } from "@web/core/registry";
import { _lt } from "@web/core/l10n/translation";
import { standardFieldProps } from "./standard_field_props";

const { Component } = owl;

export class HandleField extends Component {}

Object.assign(HandleField, {
    template: "web.HandleField",
    props: {
        ...standardFieldProps,
    },

    displayName: _lt("Handle"),
    supportedTypes: ["integer"],

    isEmpty() {
        return false;
    },
});

registry.category("fields").add("handle", HandleField);
