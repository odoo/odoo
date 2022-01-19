odoo.define('point_of_sale.PosComponent', function (require) {
    'use strict';

    const { LegacyComponent } = require("@web/legacy/legacy_component");
    const { onRendered } = owl;

    let nextId = 0;

    class PosComponent extends LegacyComponent {
        setup() {
            onRendered(() => {
                if (this.env.isDebug()) {
                    console.log('Rendered:', this.constructor.name);
                }
            });
        }
        /**
         * This function is available to all Components that inherit this class.
         * The goal of this function is to show an awaitable dialog (popup) that
         * returns a response after user interaction. See the following for quick
         * demonstration:
         *
         * ```
         * async getUserName() {
         *   const userResponse = await this.showPopup(
         *     'TextInputPopup',
         *     { title: 'What is your name?' }
         *   );
         *   // at this point, the TextInputPopup is displayed. Depending on how the popup is defined,
         *   // say the input contains the name, the result of the interaction with the user is
         *   // saved in `userResponse`.
         *   console.log(userResponse); // logs { confirmed: true, payload: <name> }
         * }
         * ```
         *
         * @param {String} name Name of the popup component
         * @param {Object} props Object that will be used to render to popup
         */
        showPopup(name, props) {
            return new Promise((resolve) => {
                this.env.posbus.trigger('show-popup', { name, props, resolve, id: nextId++ });
            });
        }
        showTempScreen(name, props) {
            return new Promise((resolve) => {
                this.trigger('show-temp-screen', { name, props, resolve });
            });
        }
        showScreen(name, props) {
            this.trigger('show-main-screen', { name, props });
        }
        /**
         * @param {String} name 'bell' | 'error'
         */
        playSound(name) {
            this.trigger('play-sound', name);
        }
        /**
         * Control the SyncNotification component.
         * @param {String} status 'connected' | 'connecting' | 'disconnected' | 'error'
         * @param {String} pending number of pending orders to sync
         */
        setSyncStatus(status, pending) {
            this.trigger('set-sync-status', { status, pending });
        }
        showNotification(message, duration = 2000) {
            this.trigger('show-notification', { message, duration });
        }
        closeNotification() {
            this.trigger('close-notification');
        }
    }

    return PosComponent;
});
