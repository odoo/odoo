import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

import { Component, onWillRender, toRaw } from "@odoo/owl";

export class LoyaltyDataField extends Component {
    static template = "sale_loyalty.LoyaltyDataField";
    static props = {
        ...standardFieldProps,
    };

    setup() {
        onWillRender(() => this.formatData());
    }

    formatData() {
        const LoyaltyCardData = this.props.record.data[this.props.name];
        this.LoyaltyCardData = Object.keys(LoyaltyCardData).length && toRaw(LoyaltyCardData);
    }

}

export const loyaltyDataField = {
    component: LoyaltyDataField,
};

registry.category("fields").add("loyalty_data_field", loyaltyDataField);
