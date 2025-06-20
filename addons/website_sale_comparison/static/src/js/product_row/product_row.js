import { Component } from '@odoo/owl';
import { formatCurrency } from '@web/core/currency';

export class ProductRow extends Component {
    static template = 'website_sale_comparison.ProductRow';
    static props = {
        id: Number,
        display_name: String,
        website_url: String,
        price: Number,
        strikethrough_price: { type: Number, optional: true },
        prevent_zero_price_sale: Boolean,
    };

    setup() {
        super.setup();
    }

    removeProduct() {
        this.env.removeProduct(this.props.productId);
    }

    /**
     * Return the price, formatted using the environment's currency.
     *
     * @return {String} The formatted price.
     */
    get formattedPrice() {
        return formatCurrency(this.props.price, this.env.currency.id);
    }

    /**
     * Return the strikethrough price, formatted using the environment's currency.
     *
     * @return {String} The formatted strikethrough price.
     */
    get formattedStrikethroughPrice() {
        return formatCurrency(this.props.strikethrough_price, this.env.currency.id);
    }
}
