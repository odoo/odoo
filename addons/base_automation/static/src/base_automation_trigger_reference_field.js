/** @odoo-module */

import { Component, xml } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { Many2OneField, many2OneField } from "@web/views/fields/many2one/many2one_field";

export class TriggerReferenceField extends Component {
    static components = { Many2OneField };
    static props = { ...Many2OneField.props };
    static template = xml`<Many2OneField t-props="m2oProps" />`;

    get m2oProps() {
        return {
            ...this.props,
            relation: this.m2oRelation,
            value: this.m2oValue,
            update: this.updateM2O.bind(this),
            canCreate: false,
            canCreateEdit: false,
            canOpen: false,
            canQuickCreate: false,
        };
    }

    get m2oRelation() {
        return this.props.record.data.trg_field_ref_model_name;
    }

    get m2oValue() {
        if (!this.value) {
            return null;
        }
        const displayName = this.props.record.data.trg_field_ref_display_name;
        return [this.value, displayName];
    }

    get value() {
        return this.props.record.data[this.props.name];
    }

    updateM2O(data) {
        const value = data[this.props.name];
        const resId = value && value[0];
        this.props.record.update({ [this.props.name]: resId });
    }
}

export const triggerReferenceField = {
    supportedTypes: ["char"],
    component: TriggerReferenceField,
    supportedOptions: many2OneField.supportedOptions,
    extractProps: many2OneField.extractProps,
};
registry.category("fields").add("base_automation_trigger_reference", triggerReferenceField);
