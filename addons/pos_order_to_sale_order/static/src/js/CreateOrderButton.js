odoo.define("point_of_sale.CreateOrderButton", function (require) {
    "use strict";

    const PosComponent = require("point_of_sale.PosComponent");
    const ProductScreen = require("point_of_sale.ProductScreen");
    const Registries = require("point_of_sale.Registries");

    class CreateOrderButton extends PosComponent {
        async onClick() {
            await this.showPopup("CreateOrderPopup", {});
        }
    }

    CreateOrderButton.template = "CreateOrderButton";

    ProductScreen.addControlButton({
        component: CreateOrderButton,
        condition: function () {
            return (
                this.env.pos.config.iface_create_sale_order &&
                this.env.pos.get_order().get_partner() &&
                this.env.pos.get_order().get_orderlines().length !== 0
            );
        },
    });

    Registries.Component.add(CreateOrderButton);

    return CreateOrderButton;
});
