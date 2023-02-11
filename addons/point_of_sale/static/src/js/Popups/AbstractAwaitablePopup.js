odoo.define('point_of_sale.AbstractAwaitablePopup', function (require) {
    'use strict';

    const { useExternalListener } = owl.hooks;
    const PosComponent = require('point_of_sale.PosComponent');

    /**
     * Implement this abstract class by extending it like so:
     * ```js
     * class ConcretePopup extends AbstractAwaitablePopup {
     *   async getPayload() {
     *     return 'result';
     *   }
     * }
     * ConcretePopup.template = owl.tags.xml`
     *   <div>
     *     <button t-on-click="confirm">Okay</button>
     *     <button t-on-click="cancel">Cancel</button>
     *   </div>
     * `
     * ```
     *
     * The concrete popup can now be instantiated and be awaited for
     * the user's response like so:
     * ```js
     * const { confirmed, payload } = await this.showPopup('ConcretePopup');
     * // based on the implementation above,
     * // if confirmed, payload = 'result'
     * //    otherwise, payload = null
     * ```
     */
    class AbstractAwaitablePopup extends PosComponent {
        constructor() {
            super(...arguments);
            if (!this.props.notEscapable) {
                useExternalListener(window, 'keyup', this._cancelAtEscape);
            }
        }
        async confirm() {
            this.props.resolve({ confirmed: true, payload: await this.getPayload() });
            this.trigger('close-popup');
        }
        cancel() {
            this.props.resolve({ confirmed: false, payload: null });
            this.trigger('close-popup');
        }
        _cancelAtEscape(event) {
            if (event.key === 'Escape') {
                this.cancel();
            }
        }
        /**
         * Override this in the concrete popup implementation to set the
         * payload when the popup is confirmed.
         */
        async getPayload() {
            return null;
        }
    }

    return AbstractAwaitablePopup;
});
