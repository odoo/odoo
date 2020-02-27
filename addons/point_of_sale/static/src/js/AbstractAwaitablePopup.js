odoo.define('point_of_sale.AbstractAwaitablePopup', function(require) {
    'use strict';

    /**
     * TODO jcb: document this
     * See `showPopup` in `point_of_sale.PosComponent` for further information.
     */

    const { PosComponent } = require('point_of_sale.PosComponent');
    const { useExternalListener } = owl.hooks;

    class AbstractAwaitablePopup extends PosComponent {
        constructor() {
            super(...arguments);
            useExternalListener(window, 'keyup', this._cancelAtEscape);
        }
        confirm() {
            this.props.resolve({ confirmed: true, payload: this.getPayload() });
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
        * TODO jcb: Establish in this docs that it is very important to override
        * this in the concrete implementation.
        *
        * This is the function that provides value to the `payload`
        * field of the result of showing this popup. It can be anything.
        * You can be creative here. Perhaps you want to send a function
        * that returns a value based on the state of this popup component.
        */
        getPayload() {
            return null;
        }
    }

    return { AbstractAwaitablePopup };
});
