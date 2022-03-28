/** @odoo-module **/

import { registry } from "@web/core/registry";
import { _lt } from "@web/core/l10n/translation";
import { standardFieldProps } from "./standard_field_props";
import { CheckBox } from "@web/core/checkbox/checkbox";

const { Component, useExternalListener, useRef } = owl;

export class BooleanField extends Component {
    setup() {
        this.root = useRef("root");
        useExternalListener(window, "click", (ev) => this.onClick(ev), { capture: true });
    }
    /**
     * @param {Event} ev
     */
    onChange(newValue) {
        this.props.update(newValue);
    }
    /**
     * @param {Event} ev
     */
    onClick(ev) {
        if (
            this.props.readonly &&
            !this.props.isDisabled &&
            ev.composedPath().includes(this.root.el)
        ) {
            this.props.update(!this.props.value);
            ev.stopPropagation();
        }
    }
    /**
     * @param {MouseEvent} ev
     */
    onKeydown({ key }) {
        switch (key) {
            case "Enter":
                this.props.update(!this.props.value);
                break;
        }
    }
}

BooleanField.template = "web.BooleanField";
BooleanField.props = {
    ...standardFieldProps,
    isDisabled: { type: Boolean, optional: true },
};
BooleanField.extractProps = (fieldName, record) => {
    return {
        isDisabled: record.isReadonly(fieldName),
    };
};
BooleanField.displayName = _lt("Checkbox");
BooleanField.supportedTypes = ["boolean"];
BooleanField.isEmpty = () => false;
BooleanField.components = { CheckBox };

registry.category("fields").add("boolean", BooleanField);
