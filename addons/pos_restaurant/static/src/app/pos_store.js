/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/pos_store";
import { PaymentScreen } from "@point_of_sale/js/Screens/PaymentScreen/PaymentScreen";
import { FloorScreen } from "@pos_restaurant/app/floor_screen/floor_screen";

const NON_IDLE_EVENTS = [
    "mousemove",
    "mousedown",
    "touchstart",
    "touchend",
    "touchmove",
    "click",
    "scroll",
    "keypress",
];
let IDLE_TIMER_SETTER;

/**
 * Go back to the floor screen if the user has been idle for a while.
 */
patch(PosStore.prototype, "pos_restaurant.PosStore", {
    /**
     * @override
     */
    setup() {
        this._super(...arguments);
        this.globalState.ready.then(() => {
            if (this.globalState.config.iface_floorplan) {
                this.setActivityListeners();
            }
        });
    },
    setActivityListeners() {
        IDLE_TIMER_SETTER = this.setIdleTimer.bind(this);
        for (const event of NON_IDLE_EVENTS) {
            window.addEventListener(event, IDLE_TIMER_SETTER);
        }
    },
    setIdleTimer() {
        clearTimeout(this.idleTimer);
        if (this.shouldResetIdleTimer()) {
            this.idleTimer = setTimeout(() => this.actionAfterIdle(), 60000);
        }
    },
    async actionAfterIdle() {
        const isPopupClosed = this.popup.closePopupsButError();
        if (isPopupClosed) {
            this.closeTempScreen();
            const { table } = this.globalState;
            const order = this.globalState.get_order();
            if (order && order.get_screen_data().name === "ReceiptScreen") {
                // When the order is finalized, we can safely remove it from the memory
                // We check that it's in ReceiptScreen because we want to keep the order if it's in a tipping state
                this.globalState.removeOrder(order);
            }
            this.showScreen("FloorScreen", { floor: table?.floor });
        }
    },
    shouldResetIdleTimer() {
        const stayPaymentScreen =
            this.mainScreen.component === PaymentScreen &&
            this.globalState.get_order().paymentlines.length > 0;
        return (
            this.globalState.config.iface_floorplan &&
            !stayPaymentScreen &&
            this.mainScreen.component !== FloorScreen
        );
    },
    showScreen(screenName) {
        if (screenName === "FloorScreen" && this.globalState.table) {
            this.globalState.unsetTable();
        }
        this._super(...arguments);
        this.setIdleTimer();
    },
    closeScreen() {
        if (this.globalState.config.iface_floorplan && !this.globalState.get_order()) {
            return this.showScreen("FloorScreen");
        }
        return this._super(...arguments);
    },
    /**
     * @override
     * Before closing pos, we remove the event listeners set on window
     * for detecting activities outside FloorScreen.
     */
    async closePos() {
        if (IDLE_TIMER_SETTER) {
            for (const event of NON_IDLE_EVENTS) {
                window.removeEventListener(event, IDLE_TIMER_SETTER);
            }
        }
        return this._super(...arguments);
    },
});
