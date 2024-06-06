/** @odoo-module **/

import { registry } from "@web/core/registry";
import { parseFloatTime } from "@web/views/fields/parsers";
import { useInputField } from "@web/views/fields/input_field_hook";
import { formatMinutes } from "./timer";
import { Component, useState } from "@odoo/owl";

/**
 * This widget is used to display the expected duration alongside the total quantity to consume of a production order.
 * The widget shows 'qty_producing_duration_expected / duration_expected', where:
 * - `qty_producing_duration_expected` is based on `qty_producing` and dynamically updates according to the `qty_producing` value.
 * - `duration_expected` is based on `qty_production` and dynamically updates according to the `qty_production` value.
 *
 * For example:
 * If the production order is created to make 5 finished products with the quantity producing set to 3,
 * the widget will display the duration based on these quantities. For instance, it might show '180:00 / 300:00',
 * where `180:00` represents the `qty_producing_duration_expected` and `300:00` represents the `duration_expected`.
 */

export class MrpQtyProducingDurationExpected extends Component {
    static template = "mrp.QtyProducingDurationExpected";
    static props = {
        record: Object,
        name: String,
        readonly: { type: Boolean, optional: true },
    };

    setup() {
        this.record = useState(this.props.record);
        this.displayQtyProducingDurationExpected = !["done", "draft", "cancel"].includes(this.record.data.state);
        useInputField({
            getValue: () => this.durationExpected,
            refName: "numpadDecimal",
            parse: (v) => parseFloatTime(v),
        });
    }

    get qtyProducingDurationExpected() {
        return formatMinutes(this.record.data.qty_producing_duration_expected);
    }

    get durationExpected() {
        return formatMinutes(this.record.data.duration_expected);
    }
}

export const mrpQtyProducingDurationExpected = {
    component: MrpQtyProducingDurationExpected,
    displayName: "MRP Qty Producing Expected Duration",
    supportedTypes: ["float"],
};

registry.category("fields").add("mrp_qty_producing_duration_expected", mrpQtyProducingDurationExpected);
