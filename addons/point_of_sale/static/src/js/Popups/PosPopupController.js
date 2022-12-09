/** @odoo-module */

import Registries from "@point_of_sale/js/Registries";
import PosComponent from "@point_of_sale/js/PosComponent";
import { useBus } from "@web/core/utils/hooks";

/**
 * This component is responsible in controlling the popups. It does so
 * by coordinating with them thru the `env.posbus`. The basic steps follow:
 * 1. `showPopup` method triggers `show-popup` event resulting to the
 *    mounting of the requested popup.
 * 2. When the popup is shown, the `confirm`/`cancel` method of the popup
 *    will be called after the popup is used. `confirming`/`cancelling`
 *    will trigger the `close-popup`, which this component also listens to,
 *    resulting to closing of the popup.
 *
 * Furthermore, Pressing `confirmKey`/`cancelKey` which defaults to
 * 'Enter'/'Escape', will automatically `confirm`/`cancel` the `topPopup`.
 * This behavior is accomplished by listening to `keyup` event of the window.
 * When the `confirmKey`/`cancelKey` of the `topPopup` is pressed,
 * 'cancel-popup-{top-popup-id}'/'confirm-popup-{top-popup-id}' will be triggered
 * and since the popup is listening to that event (@see AbstractAwaitablePopup),
 * it will result to the call of `confirm`/`cancel` method.
 *
 * @typedef {{ id: number, resolve: Function, keepBehind?: boolean, cancelKey?: string, confirmKey?: string }} BasePopupProps
 * @typedef {{ name: string, component: AbstractAwaitablePopup, props: BasePopupProps, key: string }} Popup
 */
class PosPopupController extends PosComponent {
    setup() {
        super.setup();
        useBus(this.env.posbus, "show-popup", this._showPopup);
        useBus(this.env.posbus, "close-popup", this._closePopup);
        owl.useExternalListener(window, "keyup", this._onWindowKeyup);
        this.popups = owl.useState([]);
    }
    _showPopup(event) {
        let { id, name, props, resolve } = event.detail;
        props = Object.assign(props || {}, { id, resolve });
        const component = this.constructor.components[name];
        if (!component) {
            throw new Error(
                `'${name}' is not found. Make sure the file is loaded and the component is properly registered using 'Registries.Component.add'.`
            );
        }
        if (component.dontShow) {
            resolve();
            return;
        }
        this.popups.push({
            name,
            component,
            props: this._constructPopupProps(component, props),
            key: `${name}-${id}`,
        });
    }
    _closePopup(event) {
        const { popupId, response } = event.detail;
        const index = this.popups.findIndex((popup) => popup.props.id == popupId);
        if (index != -1) {
            const popup = this.popups[index];
            popup.props.resolve(response);
            this.popups.splice(index, 1);
        }
    }
    _onWindowKeyup(event) {
        const eventIsFromInputField =
            event.target.tagName === "INPUT" || event.target.tagName === "TEXTAREA";
        const shouldHandleKey = this.topPopup && !eventIsFromInputField;
        if (!shouldHandleKey) {
            return;
        }

        if (event.key === this.topPopup.props.cancelKey) {
            this.env.posbus.trigger(`cancel-popup-${this.topPopup.props.id}`);
        } else if (event.key === this.topPopup.props.confirmKey) {
            this.env.posbus.trigger(`confirm-popup-${this.topPopup.props.id}`);
        }
    }
    /**
     * A popup can be cancelled/confirmed with 'Escape'/'Enter' key by default.
     * Also, if it's not the top popup, it is hidden from the view.
     * This can be overridden by the default props of the popop component
     * and the props used in requesting to show the popup.
     *
     * @param {AbstractAwaitablePopup} popupComponent
     * @param {Object} props
     * @returns {BasePopupProps}
     */
    _constructPopupProps(popupComponent, props) {
        const defaultProps = popupComponent.defaultProps || {};
        return Object.assign(
            {
                keepBehind: false,
                cancelKey: "Escape",
                confirmKey: "Enter",
            },
            defaultProps,
            props
        );
    }
    /**
     * @returns {boolean} Hide the element of this component when this returns false.
     */
    isShown() {
        return this.popups.length > 0;
    }
    get topPopup() {
        return this.popups[this.popups.length - 1];
    }
    /**
     * By default, only show the top popup. But always show a popup if
     * `keepBehind` props is true. Meaning, if you have 2 popups, and
     * the bottom popup has `keepBehind = true`, then the bottom popup
     * will be visible if it's not blocked in the view by the top popup.
     *
     * @param {Popup} popup
     * @returns {boolean}
     */
    shouldShow(popup) {
        return this.topPopup === popup || popup.props.keepBehind;
    }
}
PosPopupController.template = "point_of_sale.PosPopupController";
Registries.Component.add(PosPopupController);

export default PosPopupController;
