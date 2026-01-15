import { Component } from "@odoo/owl";
import { formatCurrency } from "@web/core/currency";

export class AddToCartNotification extends Component {
    static template = "website_sale.addToCartNotification";
    static props = {
        lines: {
            type: Array,
            element: {
                type: Object,
                shape: {
                    id: Number,
                    linked_line_id: { type: Number, optional: true },
                    image_url: String,
                    quantity: Number,
                    uom_name: { type: String, optional: true },
                    combination_name: { type: String, optional: true },
                    name: String,
                    description: { type: String, optional: true },
                    price_total: Number,
                },
            },
        },
        currency_id: Number,
    }

    /**
     * Return the lines which aren't linked to other lines.
     *
     * @return {Object[]} The lines which aren't linked to other lines.
     */
    get mainLines() {
        return this.props.lines.filter(line => !line.linked_line_id);
    }

    /**
     * Return the lines linked to the provided line id.
     *
     * @param {Number} lineId The id of the line whose linked lines to return.
     * @return {Object[]} The lines which aren't linked to other lines.
     */
    getLinkedLines(lineId) {
        return this.props.lines.filter(line => line.linked_line_id === lineId);
    }

    /**
     * Return the price, in the format of the sale order currency.
     *
     * @param {Object} line - The line element for which to return the formatted price.
     * @return {String} - The price, in the format of the sale order currency.
     */
    getFormattedPrice(line) {
        const linkedLines = this.getLinkedLines(line.id);
        const price = linkedLines.length
            ? linkedLines.reduce((price, linkedLine) => price + linkedLine.price_total, 0)
            : line.price_total;
        return formatCurrency(price, this.props.currency_id);
    }

}
