/** @odoo-module **/

import { registry } from "@web/core/registry";
import { _lt } from "@web/core/l10n/translation";
import { standardFieldProps } from "./standard_field_props";

const { Component } = owl;

export class PhoneField extends Component {
    /**
     * @param {Event} ev
     */
    onChange(ev) {
        this.props.update(ev.target.value);
    }
}

PhoneField.template = "web.PhoneField";
PhoneField.props = {
    ...standardFieldProps,
};
PhoneField.displayName = _lt("Phone");
PhoneField.supportedTypes = ["char"];

registry.category("fields").add("phone", PhoneField);
