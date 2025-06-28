/** @odoo-module */

/** @typedef {import("@odoo/owl").Component} Component */

/**
 * Component that has this mixin allows the use of `addControlButton`.
 * All added control buttons that satisfies the condition can be accessed
 * thru the `controlButtons` field of the Component's instance. These
 * control buttons can then be rendered in the Component.
 * @param {Function} x superclass
 */
export const ControlButtonsMixin = (x) => {
    const controlButtonsToPosition = [];
    const orderedControlButtons = [];
    let sortedControlButtons = [];

    class Extended extends x {
        get controlButtons() {
            return sortedControlButtons
                .filter((cb) => {
                    return cb.condition ? cb.condition.bind(this)() : true;
                })
                .map((cb) => Object.assign({}, cb, { component: cb.component }));
        }
    }
    /**
     * @param {Object} controlButton
     * @param {new (...args: any[]) => Component} controlButton.component the
     *      component class
     * FIXME POSREF: maybe just pass the pos explicitly to allow for arrow functions?
     * Should probably refactor this so that it's not a mixin anymore.
     * @param {Function} controlButton.condition zero argument function that is bound
     *      to the instance of ProductScreen. This gives the condition acces to
     *      the pos store and related object which it may need.
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
            orderedControlButtons.push(controlButton);
        } else {
            controlButtonsToPosition.push(controlButton);
        }
        Extended.sortControlButtons();
    };

    /**
     * Call this static method to make the added control buttons in proper
     * order.
     * NOTE: This isn't necessarily a fast algorithm. I doubt that the number
     * of control buttons will exceed an order of hundreds, so for practical
     * purposes, it is enough.
     */
    Extended.sortControlButtons = function () {
        sortedControlButtons = [...orderedControlButtons];
        function setControlButton(locator, index, cb) {
            if (locator == "replace") {
                sortedControlButtons[index] = cb;
            } else if (locator == "before") {
                sortedControlButtons.splice(index, 0, cb);
            } else if (locator == "after") {
                sortedControlButtons.splice(index + 1, 0, cb);
            }
        }
        function locate(cb) {
            const [locator, reference] = cb.position;
            const index = sortedControlButtons.findIndex((cb) => cb.name == reference);
            return [locator, index];
        }
        const cbMissingReference = [];
        // 1. First pass. If the reference control button isn't there, collect it for second pass.
        for (const cb of controlButtonsToPosition) {
            const [locator, index] = locate(cb);
            if (index == -1) {
                cbMissingReference.push(cb);
                continue;
            }
            setControlButton(locator, index, cb);
        }
        // 2. Second pass.
        // If during the first pass, 1 -> 2, 2 -> 3, 3 -> 4, 4 -> 5 and 5 is already
        // in the sorted control buttons, then 1, 2, 3 & 4 are put in `cbMissingReference`.
        // This only means 2 things about the objects in `cbMissingReference`:
        //  i) They are referencing the cb after them
        //  ii) They really have missing reference.
        // Thus, we have to iterate the cb with missing reference in reverse.
        for (const cb of cbMissingReference.reverse()) {
            const [locator, index] = locate(cb);
            if (index == -1) {
                sortedControlButtons.push(cb);
            } else {
                setControlButton(locator, index, cb);
            }
        }
    };
    return Extended;
};
