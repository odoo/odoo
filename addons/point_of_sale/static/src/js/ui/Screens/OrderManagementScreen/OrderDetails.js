/** @odoo-module alias=point_of_sale.OrderDetails **/

import PosComponent from 'point_of_sale.PosComponent';
import Orderline from 'point_of_sale.Orderline';
import OrderSummary from 'point_of_sale.OrderSummary';

/**
 * @props {'pos.order'} order
 */
class OrderDetails extends PosComponent {}
OrderDetails.components = { Orderline, OrderSummary };
OrderDetails.template = 'point_of_sale.OrderDetails';

export default OrderDetails;
