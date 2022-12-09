/** @odoo-module */

import Chrome from "@point_of_sale/js/Chrome";
import Registries from "@point_of_sale/js/Registries";

const NON_IDLE_EVENTS =
    "mousemove mousedown touchstart touchend touchmove click scroll keypress".split(/\s+/);
let IDLE_TIMER_SETTER;

const PosResChrome = (Chrome) =>
    class extends Chrome {
        /**
         * @override
         */
        async start() {
            await super.start();
            if (this.env.pos.config.iface_floorplan) {
                this._setActivityListeners();
            }
        }
        /**
         * @override
         * Do not set `FloorScreen` to the order.
         */
        _setScreenData(name) {
            if (name === "FloorScreen") {
                return;
            }
            super._setScreenData(...arguments);
        }
        /**
         * @override
         * `FloorScreen` is the start screen if there are floors.
         */
        get startScreen() {
            if (this.env.pos.config.iface_floorplan) {
                const table = this.env.pos.table;
                return { name: "FloorScreen", props: { floor: table ? table.floor : null } };
            } else {
                return super.startScreen;
            }
        }
        _setActivityListeners() {
            IDLE_TIMER_SETTER = this._setIdleTimer.bind(this);
            for (const event of NON_IDLE_EVENTS) {
                window.addEventListener(event, IDLE_TIMER_SETTER);
            }
        }
        _setIdleTimer() {
            clearTimeout(this.idleTimer);
            if (this._shouldResetIdleTimer()) {
                this.idleTimer = setTimeout(() => {
                    this._actionAfterIdle();
                }, 60000);
            }
        }
        async _actionAfterIdle() {
            const isPopupClosed = await new Promise((resolve) =>
                this.env.posbus.trigger("close-popups-but-error", { resolve })
            );
            if (isPopupClosed) {
                if (this.tempScreen.isShown) {
                    this.trigger("close-temp-screen");
                }
                const table = this.env.pos.table;
                const order = this.env.pos.get_order();
                if (order && order.get_screen_data().name === "ReceiptScreen") {
                    // When the order is finalized, we can safely remove it from the memory
                    // We check that it's in ReceiptScreen because we want to keep the order if it's in a tipping state
                    this.env.pos.removeOrder(order);
                }
                this.showScreen("FloorScreen", { floor: table ? table.floor : null });
            }
        }
        _shouldResetIdleTimer() {
            const stayPaymentScreen =
                this.mainScreen.name === "PaymentScreen" &&
                this.env.pos.get_order().paymentlines.length > 0;
            return (
                this.env.pos.config.iface_floorplan &&
                !stayPaymentScreen &&
                this.mainScreen.name !== "FloorScreen"
            );
        }
        __showScreen() {
            super.__showScreen(...arguments);
            this._setIdleTimer();
        }
        /**
         * @override
         * Before closing pos, we remove the event listeners set on window
         * for detecting activities outside FloorScreen.
         */
        async _closePos() {
            if (IDLE_TIMER_SETTER) {
                for (const event of NON_IDLE_EVENTS) {
                    window.removeEventListener(event, IDLE_TIMER_SETTER);
                }
            }
            await super._closePos();
        }
    };

Registries.Component.extend(Chrome, PosResChrome);

export default Chrome;
