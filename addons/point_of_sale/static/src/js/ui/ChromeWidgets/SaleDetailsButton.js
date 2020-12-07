/** @odoo-module alias=point_of_sale.SaleDetailsButton **/

import PosComponent from 'point_of_sale.PosComponent';

class SaleDetailsButton extends PosComponent {
    async onClick() {
        this.env.model.actionHandler({ name: 'actionPrintSalesDetails' });
    }
}
SaleDetailsButton.template = 'point_of_sale.SaleDetailsButton';

export default SaleDetailsButton;
