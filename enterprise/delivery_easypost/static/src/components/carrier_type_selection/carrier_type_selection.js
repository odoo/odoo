/** @odoo-module **/

import { registry } from "@web/core/registry";
import { SelectionField, selectionField } from "@web/views/fields/selection/selection_field";

export class CarrierTypeSelection extends SelectionField {
    get options() {
        const carrierTypes = this.props.record.context.carrier_types;
        if (carrierTypes) {
            return Object.entries(carrierTypes).map(([carrier, _]) => [carrier, carrier]);
        } else {
            return [];
        }
    }

    onChange(ev) {
        const value = JSON.parse(ev.target.value);
        if (this.type !== "char") {
            throw new Error("CarrierTypeSelecion works only for Char fields.");
        }
        this.props.record.update({ [this.props.name]: value }, { save: this.props.autosave });
    }
}

export const carrierTypeSelection = {
    ...selectionField,
    component: CarrierTypeSelection,
};

registry.category("fields").add("carrier_type_selection", carrierTypeSelection);
