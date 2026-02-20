import { CartLines } from '@website_sale/js/cart_lines/cart_lines';
import { patch } from '@web/core/utils/patch';


patch(CartLines.prototype, {
    getLineProps(line) {
        return {
            ...super.getLineProps(line),
            maxQuantity: line.max_quantity,
        }
    },
});
