/** @odoo-module alias=point_of_sale.OrderManagementButton **/

import PosComponent from 'point_of_sale.PosComponent';
import { isRpcError } from 'point_of_sale.utils';

class OrderManagementButton extends PosComponent {
    async onClick() {
        try {
            if (this.env.model.getActiveScreen() !== 'OrderManagementScreen') {
                // ping the server, if no error, show the screen
                await this.rpc({
                    model: 'pos.order',
                    method: 'browse',
                    args: [[]],
                    kwargs: { context: this.env.session.user_context },
                });
            }
            this.env.model.actionHandler({ name: 'actionToggleScreen', args: ['OrderManagementScreen'] });
        } catch (error) {
            if (isRpcError(error) && error.message.code < 0) {
                this.env.ui.askUser('ErrorPopup', {
                    title: this.env._t('Network Error'),
                    body: this.env._t('Cannot access order management screen if offline.'),
                });
            } else {
                throw error;
            }
        }
    }
}
OrderManagementButton.template = 'point_of_sale.OrderManagementButton';

export default OrderManagementButton;
