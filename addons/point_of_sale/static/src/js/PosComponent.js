odoo.define('point_of_sale.PosComponent', function(require) {
    'use strict';

    const { Component } = owl;

    class PosComponent extends Component {
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
                this.trigger('show-popup', { name, props, resolve });
            });
        }
        showTempScreen(name, props) {
            return new Promise(resolve => {
                this.trigger('show-temp-screen', { name, props, resolve });
            });
        }
        showScreen(name, props) {
            this.trigger('show-main-screen', { name, props });
        }
        /**
         * TODO jcb: This is useless! It doesn't correctly return the target.
         *      The target is still Proxy.
         *
         * Returns the target object of the proxy instance created by the
         * useState hook. (This is kinda hack.)
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

    /**
     * Extends the static `components` of parentComponent with the given components array.
     *
     * @param {Component} parentComponent
     * @param {Array<Component>} components
     */
    function addComponents(parentComponent, components) {
        if (!(parentComponent && parentComponent.prototype instanceof Component)) {
            return;
        }
        for (let component of components) {
            if (component.name in parentComponent.components) {
                console.warn(
                    `${component.name} already exists in ${parentComponent.name}'s components so it was skipped.`
                );
            } else {
                parentComponent.components[component.name] = component;
            }
        }
    }

    return { PosComponent, addComponents };
});
