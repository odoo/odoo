import { Component } from '@odoo/owl';
import { formatCurrency } from '@web/core/currency';
import comparisonUtils from '@website_sale_comparison/js/website_sale_comparison_utils';

export class ProductRow extends Component {
    static template = 'website_sale_comparison.ProductRow';
    static props = {
        id: Number,
        display_name: String,
        website_url: String,
        image_url: String,
        price: Number,
        strikethrough_price: { type: Number, optional: true },
        prevent_zero_price_sale: Boolean,
        currency_id: Number,
    };

    /**
     * Remove the product from the comparison.
     */
    removeProduct() {
        comparisonUtils.removeComparisonProduct(this.props.id, this.env.bus);
        comparisonUtils.enableDisabledProducts([this.props.id], false);
    }

    /**
     * Get the price, formatted using the provided currency.
     *
     * @return {string} The formatted price.
     */
    get formattedPrice() {
        return formatCurrency(this.props.price, this.props.currency_id);
    }

    /**
     * Get the strikethrough price, formatted using the provided currency.
     *
     * @return {string} The formatted strikethrough price.
     */
    get formattedStrikethroughPrice() {
        return formatCurrency(this.props.strikethrough_price, this.props.currency_id);
    }
}
