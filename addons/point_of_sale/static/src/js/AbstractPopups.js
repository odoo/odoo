odoo.define('point_of_sale.AbstractPopups', function(require) {
    'use strict';

    /**
     * Concrete popup components that inherit one of the `abstract` classes defined here
     * work in coordination with `showPopup` instance method of `PosComponent`.
     *
     * The responsibility of the inheriting components is to put in their views (templates) where
     * `okay` and `cancel` methods will be triggered. And if the component inherits
     * `InputPopup`, the inheriting component should also implement how `data` is assembled
     * in the `setupData` method.
     *
     * With this abstraction, we are able to come up with a dialog box (popup) that can wait
     * for user response then we can use the response for further processing.
     *
     * See `showPopup` in `point_of_sale.PosComponent` for further information.
     */

    const { Component } = owl;

    class JustOkayPopup extends Component {
        constructor() {
            super(...arguments);
            this.props = this.props || {};
            this.responded = false;
        }
        get okayText() {
            return this.props.okayText || 'Ok';
        }
        okay() {
            this.responded = true;
        }
        async getResponse() {
            return null;
        }
    }

    class OkayCancelPopup extends Component {
        constructor() {
            super(...arguments);
            this.props = this.props || {};
            this.agreed = false;
            this.responded = false;
        }
        get okayText() {
            return this.props.okayText || 'Ok';
        }
        get cancelText() {
            return this.props.cancelText || 'Cancel';
        }
        okay() {
            this.responded = true;
            this.agreed = true;
        }
        cancel() {
            this.responded = true;
            this.agreed = false;
        }
        async getResponse() {
            return this.agreed;
        }
    }

    class InputPopup extends OkayCancelPopup {
        /**
         * Override this function in the concrete inheriting class to setup
         * the value of `data`. `data` is the payload of the response of
         * this Popup. See `getResponse`.
         *
         * To allow asynchronous call, this function is made async. For instance,
         * if we want to verify in the backend whether the input is valid, we can do
         * that here. Note however that after setupData is done, regardless of
         * success or failure, the popup is closed.
         *
         * e.g.
         *
         * class NumericTextInputPopup extends InputPopup {
         *   ...
         *   async setupData() {
         *     this.data = {
         *       originalValue: this.inputRef.el.value,
         *       value: parse.float(this.inputRef.el.value),
         *     }
         *   }
         *   ...
         * }
         */
        async setupData() {
            this.data = null;
        }
        getResponse() {
            return { agreed: this.agreed, data: this.data };
        }
    }

    return { JustOkayPopup, OkayCancelPopup, InputPopup };
});
