import { CartLine } from '@website_sale/js/cart_lines/cart_line/cart_line';
import { patch } from '@web/core/utils/patch';


patch(CartLine, {
    props: {
        ...CartLine.props,
        maxQuantity: { type: Number },
    },
});
