odoo.define('point_of_sale.PopupControllerMixin', function(require) {
    'use strict';

    const { useState } = owl;
    const { useListener } = require('web.custom_hooks');

    /**
     * Allows the component declared with this mixin the ability show popup dynamically,
     * provided the following:
     *  1. The following element is declared in the template. It is where the Popup will be rendered.
     *     `<t t-if="popup.isShown" t-component="popup.component" t-props="popupProps" t-key="popup.name" />`
     *  2. The component should trigger `show-popup` event to show the popup and `close-popup` event
     *     to close. In PosComponent, `showPopup` is conveniently declared to satisfy this requirement.
     * @param {Function} x class definition to mix with during extension
     */
    const PopupControllerMixin = x =>
        class extends x {
            constructor() {
                super(...arguments);
                useListener('show-popup', this.__showPopup);
                useListener('close-popup', this.__closePopup);

                this.popup = useState({ isShown: false, name: null, component: null });
                this.popupProps = {}; // We want to avoid making the props to become Proxy!
            }
            __showPopup(event) {
                const { name, props, resolve } = event.detail;
                const popupConstructor = this.constructor.components[name];
                if (popupConstructor.dontShow) {
                    resolve();
                    return;
                }
                this.popup.isShown = true;
                this.popup.name = name;
                this.popup.component = popupConstructor;
                this.popupProps = Object.assign({}, props, { resolve });
            }
            __closePopup() {
                this.popup.isShown = false;
            }
        };

    return PopupControllerMixin;
});
