/** @odoo-module **/

import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { registry } from "@web/core/registry";
import { Component, onWillRender } from "@odoo/owl";


/**
 Widget used to display tax totals by tax groups for invoices, PO and SO,
 and possibly allowing editing them.

 Note that this widget requires the object it is used on to have a
 currency_id field.
 **/
export class LoyaltyCardSummariesComponent extends Component {
    static template = "sale_loyalty.SummariesComponent";
    static props = { ...standardFieldProps };

    setup() {
        this.history = {};
        onWillRender(() => this.formatData());
    }

    formatData() {
        console.log("this.props.record.data[this.props.name].records");
        console.log(this.props.record.data[this.props.name].records);
        this.history = this.props.record.data[this.props.name].records.reduce(
            function(accumulator, record) {
                if (record.data.program_type != 'loyalty') {
                    return accumulator;
                }
                if (accumulator[record.data.coupon_id]){
                    accumulator[record.data.coupon_id].used += currentValue.used;
                    accumulator[record.data.coupon_id].issued += currentValue.issued;
                } else {
                    accumulator[record.data.coupon_id] = {
                        coupon_id: record.data.coupon_id,
                        program_name: record.data.program_name,
                        balance: record.data.balance,
                        used: record.data.used,
                        issued: record.data.issued,
                    }
                }
                return accumulator;
            },
            {}
        );
    }
}

export const loyaltyCardSummariesComponent = {
    component: LoyaltyCardSummariesComponent,
    supportedTypes: ["one2many"],
    relatedFields: [
            { name: "coupon_id", type: "int" },
            { name: "program_type", type: "char" },
            { name: "program_name", type: "char" },
            { name: "balance", type: "float" },
            { name: "used", type: "float" },
            { name: "issued", type: "float" },
        ],
};

registry.category("fields").add("sale-loyalty-summaries-field", loyaltyCardSummariesComponent);
