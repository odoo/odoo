/** @odoo-module alias=point_of_sale.OrderReceipt **/

import PosComponent from 'point_of_sale.PosComponent';
import WrappedProductNameLines from 'point_of_sale.WrappedProductNameLines';
import { float_is_zero } from 'web.utils';

class OrderReceipt extends PosComponent {
    _isTaxIncluded(receipt) {
        return float_is_zero(receipt.subtotal - receipt.total_with_tax, this.env.model.currency.decimal_places);
    }
    _isSimple(line) {
        return (
            line.discount === 0 &&
            line.unit_name === 'Units' &&
            line.quantity === 1 &&
            !(line.display_discount_policy == 'without_discount' && line.price < line.price_lst)
        );
    }
    _showRoundingInfo(receipt) {
        return receipt.is_payment_rounded;
    }
}
OrderReceipt.components = { WrappedProductNameLines };
OrderReceipt.template = 'point_of_sale.OrderReceipt';

export default OrderReceipt;
