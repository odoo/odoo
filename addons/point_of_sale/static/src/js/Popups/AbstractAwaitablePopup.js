/** @odoo-module */

import PosComponent from "@point_of_sale/js/PosComponent";
import { useBus } from "@web/core/utils/hooks";

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
 * const { confirmed, payload } = await this.showPopup('ConcretePopup');
 * // based on the implementation above,
 * // if confirmed, payload = 'result'
 * //    otherwise, payload = null
 * ```
 */
class AbstractAwaitablePopup extends PosComponent {
    setup() {
        super.setup();
        if (this.props.confirmKey) {
            useBus(this.env.posbus, `confirm-popup-${this.props.id}`, this.confirm);
        }
        if (this.props.cancelKey) {
            useBus(this.env.posbus, `cancel-popup-${this.props.id}`, this.cancel);
        }
    }
    async confirm() {
        this.env.posbus.trigger("close-popup", {
            popupId: this.props.id,
            response: { confirmed: true, payload: await this.getPayload() },
        });
    }
    cancel() {
        this.env.posbus.trigger("close-popup", {
            popupId: this.props.id,
            response: { confirmed: false, payload: null },
        });
    }
    /**
     * Override this in the concrete popup implementation to set the
     * payload when the popup is confirmed.
     */
    async getPayload() {
        return null;
    }
}

export default AbstractAwaitablePopup;
