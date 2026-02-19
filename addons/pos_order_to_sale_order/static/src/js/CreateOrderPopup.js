odoo.define("point_of_sale.CreateOrderPopup", function (require) {
    "use strict";

    const AbstractAwaitablePopup = require("point_of_sale.AbstractAwaitablePopup");
    const Registries = require("point_of_sale.Registries");
    const framework = require("web.framework");

    class CreateOrderPopup extends AbstractAwaitablePopup {
        setup() {
            super.setup();
            this.createOrderClicked = false;
        }

        async createDraftSaleOrder() {
            await this._actionCreateSaleOrder("draft");
        }

        async createConfirmedSaleOrder() {
            await this._actionCreateSaleOrder("confirmed");
        }

        async createDeliveredSaleOrder() {
            await this._actionCreateSaleOrder("delivered");
        }

        async createInvoicedSaleOrder() {
            await this._actionCreateSaleOrder("invoiced");
        }

        async _actionCreateSaleOrder(order_state) {
            // Create Sale Order
            await this._createSaleOrder(order_state);

            // Delete current order
            const current_order = this.env.pos.get_order();
            this.env.pos.removeOrder(current_order);
            this.env.pos.add_new_order();

            // Close popup
            return await super.confirm();
        }

        async _createSaleOrder(order_state) {
            const current_order = this.env.pos.get_order();
            framework.blockUI();
            return await this.rpc({
                model: "sale.order",
                method: "create_order_from_pos",
                args: [current_order.export_as_JSON(), order_state],
            })
                .catch(function (error) {
                    throw error;
                })
                .finally(function () {
                    framework.unblockUI();
                });
        }
    }

    CreateOrderPopup.template = "CreateOrderPopup";
    Registries.Component.add(CreateOrderPopup);

    return CreateOrderPopup;
});
