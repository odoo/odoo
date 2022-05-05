/** @odoo-module **/

import { registry } from "@web/core/registry";
import { _lt } from "@web/core/l10n/translation";
import { useInputField } from "./input_field_hook";
import { standardFieldProps } from "./standard_field_props";

const { Component } = owl;

export class PhoneField extends Component {
    setup() {
        useInputField({ getValue: () => this.props.value || "" });
    }

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
