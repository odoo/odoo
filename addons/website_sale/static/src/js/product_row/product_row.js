import { Component, t, useProps } from '@odoo/owl';
import { formatCurrency } from '@web/core/currency';
import comparisonUtils from '@website_sale/js/comparison_utils';

export class ProductRow extends Component {
    static template = 'website_sale.ProductRow';
    props = useProps({
        id: t.number(),
        display_name: t.string(),
        website_url: t.string(),
        image_url: t.string(),
        price: t.number(),
        strikethrough_price: t.number().optional(),
        hide_price: t.boolean(),
        currency_id: t.number(),
    });

    /**
     * Remove the product from the comparison.
     */
    removeProduct() {
        comparisonUtils.removeComparisonProduct(this.props.id, this.env.bus);
        comparisonUtils.enableAddToComparisonButtons([this.props.id], false);
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
