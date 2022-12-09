/** @odoo-module */

import PosComponent from "@point_of_sale/js/PosComponent";
import ProductScreen from "@point_of_sale/js/Screens/ProductScreen/ProductScreen";
import Registries from "@point_of_sale/js/Registries";

/**
 * IMPROVEMENT: Perhaps this class is quite complicated for its worth.
 * This is because it needs to listen to changes to the current order.
 * Also, the current order changes when the selectedOrder in pos is changed.
 * After setting new current order, we update the listeners.
 */
class SubmitOrderButton extends PosComponent {
    setup() {
        super.setup();
        this.clicked = false; //mutex, we don't want to be able to spam the printers
    }
    async _onClick() {
        if (!this.clicked) {
            try {
                this.clicked = true;
                const order = this.env.pos.get_order();
                if (order.hasChangesToPrint()) {
                    const isPrintSuccessful = await order.printChanges();
                    if (isPrintSuccessful) {
                        order.updatePrintedResume();
                    } else {
                        this.showPopup("ErrorPopup", {
                            title: this.env._t("Printing failed"),
                            body: this.env._t("Failed in printing the changes in the order"),
                        });
                    }
                }
            } finally {
                this.clicked = false;
            }
        }
    }
    get currentOrder() {
        return this.env.pos.get_order();
    }
    get addedClasses() {
        if (!this.currentOrder) {
            return {};
        }
        const hasChanges = this.currentOrder.hasChangesToPrint();
        const skipped = hasChanges ? false : this.currentOrder.hasSkippedChanges();
        return {
            highlight: hasChanges,
            altlight: skipped,
        };
    }
}
SubmitOrderButton.template = "SubmitOrderButton";

ProductScreen.addControlButton({
    component: SubmitOrderButton,
    condition: function () {
        return this.env.pos.config.module_pos_restaurant && this.env.pos.unwatched.printers.length;
    },
});

Registries.Component.add(SubmitOrderButton);

export default SubmitOrderButton;
