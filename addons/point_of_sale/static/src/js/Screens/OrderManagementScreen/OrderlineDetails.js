odoo.define('point_of_sale.OrderlineDetails', function (require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');
    const { format } = require('web.field_utils');
    const { round_precision: round_pr } = require('web.utils');

    /**
     * @props {pos.order.line} line
     */
    class OrderlineDetails extends PosComponent {
        get line() {
            const line = this.props.line;
            const formatQty = (line) => {
                const quantity = line.get_quantity();
                const unit = line.get_unit();
                const decimals = this.env.pos.dp['Product Unit of Measure'];
                const rounding = Math.max(unit.rounding, Math.pow(10, -decimals));
                const roundedQuantity = round_pr(quantity, rounding);
                return format.float(roundedQuantity, { digits: [69, decimals] });
            };
            return {
                productName: line.get_full_product_name(),
                totalPrice: line.get_price_with_tax(),
                quantity: formatQty(line),
                unit: line.get_unit().name,
                unitPrice: line.get_unit_price(),
            };
        }
        get productName() {
            return this.line.productName;
        }
        get totalPrice() {
            return this.env.pos.format_currency(this.line.totalPrice);
        }
        get quantity() {
            return this.line.quantity;
        }
        get unitPrice() {
            return this.line.unitPrice;
        }
        get unit() {
            return this.line.unit;
        }
        get pricePerUnit() {
            return ` ${this.unit} at ${this.unitPrice} / ${this.unit}`;
        }
    }
    OrderlineDetails.template = 'OrderlineDetails';

    Registries.Component.add(OrderlineDetails);

    return OrderlineDetails;
});
