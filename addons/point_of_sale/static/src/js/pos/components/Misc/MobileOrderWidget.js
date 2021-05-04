/** @odoo-module alias=point_of_sale.MobileOrderWidget **/

import PosComponent from 'point_of_sale.PosComponent';

/**
 * @prop {string} pane
 * @prop {'pos.order'} order
 */
class MobileOrderWidget extends PosComponent {
    constructor() {
        super(...arguments);
        this.pane = this.props.pane;
    }
    get total() {
        const { withTaxWithDiscount } = this.env.model.getOrderTotals(this.props.order);
        return this.env.model.formatCurrency(withTaxWithDiscount);
    }
    get items_number() {
        if (!this.props.order) return 0;
        const orderlines = this.env.model.getOrderlines(this.props.order);
        return orderlines.reduce((items_number, line) => items_number + line.qty, 0);
    }
}
MobileOrderWidget.template = 'point_of_sale.MobileOrderWidget';

export default MobileOrderWidget;
