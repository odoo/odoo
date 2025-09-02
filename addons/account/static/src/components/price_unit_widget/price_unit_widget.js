import { onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

import { registry } from "@web/core/registry";
import { floatField, FloatField } from "@web/views/fields/float/float_field";


class PriceUnitWidget extends FloatField {
    setup() {
        super.setup();
        this.orm = useService("orm");
        onWillStart(async () => {
            if (this.props.name === 'price_unit') {
                this.minDecimals = await this.orm.call(
                    "decimal.precision",
                    "precision_get",
                    ['Product Price'],
                );
            }
        })
    }

    get formattedValue() {
        const [_intPart, decPart = ""] = this.value.toString().split(".");
        let digits;
        if (decPart.length < this.minDecimals) {
            digits = this.minDecimals;
        } else {
            digits = Math.min(8, decPart.length);
        }
        this.props.digits = [16, digits];
        return super.formattedValue;
    }
}

const priceUnitWidget = {
    ...floatField,
    component: PriceUnitWidget,
}

registry.category("fields").add("price_unit_widget", priceUnitWidget);
