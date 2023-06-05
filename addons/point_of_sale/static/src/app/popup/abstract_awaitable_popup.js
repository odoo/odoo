/** @odoo-module */

import { Component, useExternalListener } from "@odoo/owl";

/**
 * Implement this abstract class by extending it like so:
 * ```js
 * class ConcretePopup extends AbstractAwaitablePopup {
 *   async getPayload() {
 *     return 'result';
 *   }
 * }
 * ConcretePopup.template = xml`
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
 * const { confirmed, payload } = await this.popup.add(ConcretePopup);
 * // based on the implementation above,
 * // if confirmed, payload = 'result'
 * //    otherwise, payload = null
 * ```
 */
export class AbstractAwaitablePopup extends Component {
    setup() {
        super.setup(...arguments);
        useExternalListener(window, "keyup", this._onWindowKeyup);
    }
    _onWindowKeyup(event) {
        if (!this.props.isActive || ["INPUT", "TEXTAREA"].includes(event.target.tagName)) {
            return;
        }
        if (event.key === this.props.cancelKey) {
            this.cancel();
        } else if (event.key === this.props.confirmKey) {
            this.confirm();
        }
    }
    async confirm() {
        this.props.close({ confirmed: true, payload: await this.getPayload() });
    }
    cancel() {
        this.props.close({ confirmed: false, payload: null });
    }
    /**
     * Override this in the concrete popup implementation to set the
     * payload when the popup is confirmed.
     */
    async getPayload() {
        return null;
    }
}
