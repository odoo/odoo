odoo.define('point_of_sale.PosComponent', function(require) {
    'use strict';

    const { until } = require('point_of_sale.utils');
    const { popupsRegistry } = require('point_of_sale.popupsRegistry');

    class PosComponent extends owl.Component {
        /**
         * This function is available to all Components that inherits this class.
         * The goal of this function is to show an awaitable dialog (popup) that
         * returns a response after user interaction. See the following for quick
         * demonstration:
         *
         * getUserName() {
         *   const userResponse = await this.showPopup('TextInputPopup', { title: 'What is your name?' });
         *   // at this point, the TextInputPopup is displayed. Depending on how the popup is defined,
         *   // say the input contains the name, the result of the interaction with the user is
         *   // saved in `userResponse`.
         *   console.log(userResponse); // logs { agreed: true, data: <name> }
         * }
         *
         * @param {String} name Name of the popup component
         * @param {Object} props Object that will be used to render to popup
         * @param {*} automaticResponse Optional. If provided, the return promise
         *      immediate resolves to this value.
         */
        async showPopup(name, props, automaticResponse = null) {
            let popup;
            try {
                if (automaticResponse) {
                    return automaticResponse;
                } else {
                    const popupComponent = popupsRegistry.get(name);
                    popup = new popupComponent(this, props);
                    popup.mount(document.getElementsByClassName('pos')[0] || document.body);
                    await until(() => popup.responded);
                    if (popup.agreed && popup.setupData) {
                        await popup.setupData();
                    }
                    return popup.getResponse();
                }
            } catch (error) {
                throw error;
            } finally {
                popup && popup.unmount();
            }
        }
    }
    PosComponent.addComponents = function(components) {
        for (let component of components) {
            if (this.components[component.name]) {
                console.error(
                    `${component.name} already exists in ${this.name}'s components so it was skipped.`
                );
            } else {
                this.components[component.name] = component;
            }
        }
    };

    return { PosComponent };
});
