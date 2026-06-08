import { Product } from '@sale/js/product/product';
import { patch } from '@web/core/utils/patch';

patch(Product, {
    props: {
        ...Product.props,
        strikethrough_price: { type: Number, optional: true },
        base_unit_price: { type: Number, optional: true },
        can_be_sold: { type: Boolean, optional: true },
        // The following fields are needed for tracking.
        category_name: { type: String, optional: true },
        currency_name: { type: String, optional: true },
    },
});
