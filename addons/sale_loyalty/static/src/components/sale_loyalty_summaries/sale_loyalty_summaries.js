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
        this.coupon_point_ids = {};
        this.data = [];
        onWillRender(() => this.formatData(this.props));
    }

    getCouponPointProps(record) {
        return {
            program_name: record.data.program_name,
            points_balanced: record.data.points_balanced,
            points_used: record.data.points_used,
            points_issued: record.data.points_issued,
        };
    }

    get couponPoints() {
        return this.props.record.data[this.props.name].records.map((record) =>
            this.getCouponPointProps(record)
        );
    }

    formatData(props) {
        this.data = this.props.record.data[this.props.name].records;
        console.log("this.data");
        console.log(this.data);
        // console.log('propspropspropspropspropspropspropspropspropspropspropspropspropspropspropspropspropspropspropsprops')
        // console.log(props)
        // console.log("HELLO");
        // console.log("props.record.data[this.props.name]")
        // console.log(props.record.data[this.props.name])
        // console.log("toRaw(props.record.data[this.props.name])")
        // console.log(toRaw(props.record.data[this.props.name]))
        // console.log("JSON.stringify(toRaw(props.record.data[this.props.name]))")
        // console.log(JSON.stringify(toRaw(props.record.data[this.props.name])))
        // this.coupon_point_ids = JSON.parse(JSON.stringify(toRaw(props.record.data[this.props.name])));
        // console.log(this.coupon_point_ids)
        // if (!totals) {
        //     return;
        // }
        // const currencyFmtOpts = { currencyId: props.record.data.currency_id && props.record.data.currency_id[0] };

        // let amount_untaxed = totals.amount_untaxed;
        // let amount_tax = 0;
        // let subtotals = [];
        // for (let subtotal_title of totals.subtotals_order) {
        //     let amount_total = amount_untaxed + amount_tax;
        //     subtotals.push({
        //         'name': subtotal_title,
        //         'amount': amount_total,
        //         'formatted_amount': formatMonetary(amount_total, currencyFmtOpts),
        //     });
        //     let group = totals.groups_by_subtotal[subtotal_title];
        //     for (let i in group) {
        //         amount_tax = amount_tax + group[i].tax_group_amount;
        //     }
        // }
        // totals.subtotals = subtotals;
        // let rounding_amount = totals.display_rounding && totals.rounding_amount || 0;
        // let amount_total = amount_untaxed + amount_tax + rounding_amount;
        // totals.amount_total = amount_total;
        // totals.formatted_amount_total = formatMonetary(amount_total, currencyFmtOpts);
        // for (let group_name of Object.keys(totals.groups_by_subtotal)) {
        //     let group = totals.groups_by_subtotal[group_name];
        //     for (let key in group) {
        //         group[key].formatted_tax_group_amount = formatMonetary(group[key].tax_group_amount, currencyFmtOpts);
        //         group[key].formatted_tax_group_base_amount = formatMonetary(group[key].tax_group_base_amount, currencyFmtOpts);
        //     }
        // }
        // this.totals = totals;
    }
}

export const loyaltyCardSummariesComponent = {
    component: LoyaltyCardSummariesComponent,
    supportedTypes: ["one2many"],
    relatedFields: [
            { name: "program_name", type: "char" },
            { name: "points_balanced", type: "float" },
            { name: "points_used", type: "float" },
            { name: "points_issued", type: "float" },
        ],
};

registry.category("fields").add("sale-loyalty-summaries-field", loyaltyCardSummariesComponent);
