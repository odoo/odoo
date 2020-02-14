odoo.define('point_of_sale.PosComponent', function(require) {
    'use strict';

    class PosComponent extends owl.Component {
        /**
         * This function is available to all Components that inherits this class.
         * The goal of this function is to show an awaitable dialog (popup) that
         * returns a response after user interaction. See the following for quick
         * demonstration:
         *
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
         *
         * @param {String} name Name of the popup component
         * @param {Object} props Object that will be used to render to popup
         */
        showPopup(name, props) {
            return new Promise(resolve => {
                this.trigger('show-popup', { name, props, __theOneThatWaits: { resolve } });
            });
        }
        /**
         * Returns the target object of the proxy instance created by the
         * useState hook.
         *
         * e.g.
         *
         * -- in the constructor --
         * this.state = useState({ val: 1 })
         * // this.state is a Proxy instance of the Observer
         *
         * -- in other methods --
         * const stateTarget = this.getStateTarget(this.state)
         * // stateTarget is now { val: <latestVal> } and is not Proxy.
         *
         * @param {Proxy} state state or Observer proxy object.
         */
        getStateTarget(state) {
            return this.__owl__.observer.weakMap.get(state).value;
        }
    }
    PosComponent.addComponents = function(components) {
        for (let component of components) {
            if (this.components[component.name]) {
                console.warn(
                    `${component.name} already exists in ${this.name}'s components so it was skipped.`
                );
            } else {
                this.components[component.name] = component;
            }
        }
    };

    return { PosComponent };
});
