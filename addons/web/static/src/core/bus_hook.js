/** @odoo-module **/

const { onMounted, onWillUnmount, useComponent } = owl.hooks;

/**
 * This file contains various custom hooks.
 * Their inner working is rather simple:
 * Each custom hook simply hook itself to any number of owl lifecycle hooks.
 * You can then use them just like an owl hook in any Component
 * e.g.:
 * import { useBus } from "@web/core/bus_hook";
 * ...
 * setup() {
 *    ...
 *    useBus(someBus, someEvent, callback)
 *    ...
 * }
 */

// -----------------------------------------------------------------------------
// Hook functions
// -----------------------------------------------------------------------------

/**
 * Ensures a bus event listener is attached and cleared the proper way.
 *
 * @param {EventBus} bus
 * @param {string} eventName
 * @param {Callback} callback
 */
export function useBus(bus, eventName, callback) {
    const component = useComponent();
    onMounted(() => bus.on(eventName, component, callback));
    onWillUnmount(() => bus.off(eventName, component));
}
