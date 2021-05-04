/** @odoo-module alias=point_of_sale.ActionpadWidget **/

import PosComponent from 'point_of_sale.PosComponent';

/**
 * @props client
 * @emits click-customer
 * @emits click-pay
 */
class ActionpadWidget extends PosComponent {
    get isLongName() {
        return this.client && this.client.name.length > 10;
    }
    get client() {
        return this.props.client;
    }
}
ActionpadWidget.template = 'point_of_sale.ActionpadWidget';

export default ActionpadWidget;
