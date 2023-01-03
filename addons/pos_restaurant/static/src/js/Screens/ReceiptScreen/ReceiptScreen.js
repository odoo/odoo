/** @odoo-module */

import ReceiptScreen from "@point_of_sale/js/Screens/ReceiptScreen/ReceiptScreen";
import Registries from "@point_of_sale/js/Registries";

const PosResReceiptScreen = (ReceiptScreen) =>
    class extends ReceiptScreen {
        //@override
        _addNewOrder() {
            if (!this.env.pos.config.iface_floorplan) {
                super._addNewOrder();
            }
        }
        //@override
        get nextScreen() {
            if (this.env.pos.config.iface_floorplan) {
                const table = this.env.pos.table;
                return { name: "FloorScreen", props: { floor: table ? table.floor : null } };
            } else {
                return super.nextScreen;
            }
        }
        onBackToFloorButtonClick() {
            // If we're here and the order is paid, we can remove it from the orders
            this.env.pos.removeOrder(this.currentOrder);
        }
    };

Registries.Component.extend(ReceiptScreen, PosResReceiptScreen);

export default ReceiptScreen;
