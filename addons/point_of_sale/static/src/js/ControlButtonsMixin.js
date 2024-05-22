odoo.define('point_of_sale.ControlButtonsMixin', function (require) {
    'use strict';

    const Registries = require('point_of_sale.Registries');

    /**
     * Component that has this mixin allows the use of `addControlButton`.
     * All added control buttons that satisfies the condition can be accessed
     * thru the `controlButtons` field of the Component's instance. These
     * control buttons can then be rendered in the Component.
     * @param {Function} x superclass
     */
    const ControlButtonsMixin = (x) => {
        class Extended extends x {
            get controlButtons() {
                return this.constructor.controlButtons
                    .filter((cb) => {
                        return cb.condition.bind(this)();
                    })
                    .map((cb) =>
                        Object.assign({}, cb, { component: Registries.Component.get(cb.component) })
                    );
            }
        }
        Extended.controlButtons = [];
        /**
         * @param {Object} controlButton
         * @param {Function} controlButton.component
         *      Base class that is added in the Registries.Component.
         * @param {Function} controlButton.condition zero argument function that is bound
         *      to the instance of ProductScreen, such that `this.env.pos` can be used
         *      inside the function.
         * @param {Array} [controlButton.position] array of two elements
         *      [locator, relativeTo]
         *      locator: string -> any of ('before', 'after', 'replace')
         *      relativeTo: string -> other controlButtons component name
         */
        Extended.addControlButton = function (controlButton) {
            // We set the name first.
            if (!controlButton.name) {
                controlButton.name = controlButton.component.name;
            }

            // If no position is set, we just push it to the array.
            if (!controlButton.position) {
                this.controlButtons.push(controlButton);
            } else {
                // Find where to put the new controlButton.
                const [locator, relativeTo] = controlButton.position;
                let whereIndex = -1;
                for (let i = 0; i < this.controlButtons.length; i++) {
                    if (this.controlButtons[i].name === relativeTo) {
                        if (['before', 'replace'].includes(locator)) {
                            whereIndex = i;
                        } else if (locator === 'after') {
                            whereIndex = i + 1;
                        }
                        break;
                    }
                }

                // If found where to put, then perform the necessary mutation of
                // the buttons array.
                // Else, we just push this controlButton to the array.
                if (whereIndex > -1) {
                    this.controlButtons.splice(
                        whereIndex,
                        locator === 'replace' ? 1 : 0,
                        controlButton
                    );
                } else {
                    let warningMessage =
                        `'${controlButton.name}' has invalid 'position' ([${locator}, ${relativeTo}]).` +
                        'It is pushed to the controlButtons stack instead.';
                    console.warn(warningMessage);
                    this.controlButtons.push(controlButton);
                }
            }
        };
        return Extended;
    };

    return ControlButtonsMixin;
});
