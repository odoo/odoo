/** @odoo-module */

import ReceiptScreen from "@point_of_sale/js/Screens/ReceiptScreen/ReceiptScreen";
import Registries from "@point_of_sale/js/Registries";
import { usePos } from "@point_of_sale/app/pos_store";
import { onWillUnmount } from "@odoo/owl";

const PosResReceiptScreen = (ReceiptScreen) =>
    class extends ReceiptScreen {
        static showBackToFloorButton = true;
        setup() {
            super.setup();
            this.pos = usePos();
            onWillUnmount(() => {
                // When leaving the receipt screen to the floor screen the order is paid and can be removed
                if (this.pos.mainScreen.name === "FloorScreen" && this.currentOrder.finalized) {
                    this.env.pos.removeOrder(this.currentOrder);
                }
            });
        }
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
    };

Registries.Component.extend(ReceiptScreen, PosResReceiptScreen);

export default ReceiptScreen;
