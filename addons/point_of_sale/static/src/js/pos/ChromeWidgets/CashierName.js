/** @odoo-module alias=point_of_sale.CashierName **/

import PosComponent from 'point_of_sale.PosComponent';

// Previously UsernameWidget
class CashierName extends PosComponent {}
CashierName.template = 'point_of_sale.CashierName';

export default CashierName;
