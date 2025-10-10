import { Component } from '@odoo/owl';
import { formatCurrency } from '@web/core/currency';


/**
 * @typedef {Object} CartNotificationLineType
 * @property {Number} id
 * @property {Number} [linkedLineId]
 * @property {String} imageSrc
 * @property {Number} quantity
 * @property {String} [uomName]
 * @property {String} [combinationName]
 * @property {String} name
 * @property {String} [description]
 * @property {Number} priceTotal
 *
 * @typedef {Object} ItemAddedNotificationType
 * @property {CartNotificationLineType[]} lines
 * @property {Number} currencyId
 */
export class ItemAddedNotification extends Component {
    static template = 'website_sale.itemAddedNotification';
    /** @type { ItemAddedNotificationType } */
    static props = {
        lines: {
            type: Array,
            element: {
                type: Object,
                shape: {
                    id: Number,
                    linkedLineId: { type: Number, optional: true },
                    imageSrc: String,
                    quantity: Number,
                    uomName: { type: String, optional: true },
                    combinationName: { type: String, optional: true },
                    name: String,
                    description: { type: String, optional: true },
                    priceTotal: Number,
                },
            },
        },
        currencyId: Number,
    }

    /**
     * Return the lines which aren't linked to other lines.
     *
     * @return {CartNotificationLineType[]} - The lines which aren't linked to other lines.
     */
    get mainLines() {
        return this.props.lines.filter(line => !line.linkedLineId);
    }

    /**
     * Return the lines linked to the provided line id.
     *
     * @param {Number} - lineId The id of the line whose linked lines to return.
     * @return {CartNotificationLineType[]} - The lines which aren't linked to other lines.
     */
    getLinkedLines(lineId) {
        return this.props.lines.filter(line => line.linkedLineId === lineId);
    }

    /**
     * Return the price, in the format of the sale order currency.
     *
     * @param {CartNotificationLineType} line - The line element for which to return the formatted price.
     * @return {String} - The price, in the format of the sale order currency.
     */
    getFormattedPrice(line) {
        const linkedLines = this.getLinkedLines(line.id);
        const price = linkedLines.length
            ? linkedLines.reduce((price, linkedLine) => price + linkedLine.priceTotal, 0)
            : line.priceTotal;
        return formatCurrency(price, this.props.currencyId);
    }

}
