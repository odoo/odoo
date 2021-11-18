/** @odoo-module **/

import { registry } from "@web/core/registry";
import { standardFieldProps } from "./standard_field_props";

const { Component } = owl;

export class HandleField extends Component {}

Object.assign(HandleField, {
    props: {
        ...standardFieldProps,
    },
    template: "web.HandleField",
    isEmpty() {
        return false;
    },
});

registry.category("fields").add("handle", HandleField);
