/** @odoo-module **/

import { registry } from "@web/core/registry";
import { _lt } from "@web/core/l10n/translation";
import { standardFieldProps } from "../standard_field_props";

import { Component } from "@odoo/owl";

export class HandleField extends Component {}

HandleField.template = "web.HandleField";
HandleField.props = {
    ...standardFieldProps,
};
HandleField.displayName = _lt("Handle");
HandleField.supportedTypes = ["integer"];
HandleField.isEmpty = () => false;

registry.category("fields").add("handle", HandleField);
