import { Product } from '@sale/js/product/product';
import { formatCurrency } from '@web/core/currency';
import { patch } from '@web/core/utils/patch';

patch(Product, {
    props: {
        ...Product.props,
        strikethrough_price: { type: Number, optional: true },
        can_be_sold: { type: Boolean, optional: true },
        // The following fields are needed for tracking.
        category_name: { type: String, optional: true },
        currency_name: { type: String, optional: true },
    },
});

patch(Product.prototype, {
    /**
     * Return the strikethrough price, formatted using the environment's currency.
     *
     * @return {String} - The formatted strikethrough price.
     */
    get formattedStrikethroughPrice() {
        return formatCurrency(this.props.strikethrough_price, this.env.currency.id);
    },
});
