odoo.define('point_of_sale.ReprintReceiptButton', function (require) {
    'use strict';

    const { useListener } = require('web.custom_hooks');
    const { useContext } = owl.hooks;
    const PosComponent = require('point_of_sale.PosComponent');
    const OrderManagementScreen = require('point_of_sale.OrderManagementScreen');
    const Registries = require('point_of_sale.Registries');
    const contexts = require('point_of_sale.PosContext');

    class ReprintReceiptButton extends PosComponent {
        constructor() {
            super(...arguments);
            useListener('click', this._onClick);
            this.orderManagementContext = useContext(contexts.orderManagement);
        }
        async _onClick() {
            const order = this.orderManagementContext.selectedOrder;
            if (!order) return;

            if (this.env.pos.proxy.printer) {
                const receiptHtml = this.props.hiddenOrderReceipt.el.outerHTML;
                const printResult = await this.env.pos.proxy.printer.print_receipt(receiptHtml);
                if (!printResult.successful) {
                    this.showTempScreen('ReprintReceiptScreen', { order: order });
                }
            } else {
                this.showTempScreen('ReprintReceiptScreen', { order: order });
            }
        }
    }
    ReprintReceiptButton.template = 'ReprintReceiptButton';

    OrderManagementScreen.addControlButton({
        component: ReprintReceiptButton,
        condition: function () {
            return true;
        },
    });

    Registries.Component.add(ReprintReceiptButton);

    return ReprintReceiptButton;
});
