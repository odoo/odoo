/* @odoo-module */

/**
 * Use this mixin to create a component that will be shown in fullscreen.
 * (Technically, the currently shown screen is hidden, not unmounted, in order
 * to show this screen.) The declared screen that uses this mixin should bind
 * `closeWith` to some event that will be triggered by the user; or, call it
 * inside another method. Calling `closeWith` closes the temporary screen.
 *
 * The temporary screen can be shown anytime by any PosComponent like so:
 *
 * ```
 * const { confirmed, payload } = await this.showTempScreen(popupScreenName, screenProps);
 * ```
 *
 * When the screen closes, call to `showTempScreen` resolves to a record
 * `{ confirmed: boolean, payload?: any }`. This mimics a dialog-like feature.
 */
const TemporaryScreenMixin = function (Component) {
    class TemporaryScreen extends Component {
        /**
         * Assign this method to an event handler like so:
         *
         * ```xml
         *  <div t-on-click="() => this.closeWith(true, payload)">Button</div>
         * ```
         *
         * or call it inside another method:
         *
         * ```js
         * _onAnotherMethod() {
         *   // do something, say compute the payload
         *   this.closeWith(true, payload);
         * }
         * ```
         * @param {boolean} confirmed - is a boolean representing whether the user confirmed the screen or not
         * @param {any} payload - is any information sent to the caller of `showTempScreen`.
         */
        closeWith(confirmed, payload) {
            this.trigger('close-temp-screen', { confirmed, payload });
        }
    }

    // Mark the component as a temporary screen.
    TemporaryScreen.isTempScreen = true;

    return TemporaryScreen;
};

export default TemporaryScreenMixin;
