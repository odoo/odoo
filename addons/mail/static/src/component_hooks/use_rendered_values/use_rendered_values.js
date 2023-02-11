/** @odoo-module **/

const { Component } = owl;
const { onMounted, onPatched } = owl.hooks;

/**
 * This hooks provides support for accessing the values returned by the given
 * selector at the time of the last render. The values will be updated after
 * every mount/patch.
 *
 * @param {function} selector function that will be executed at the time of the
 *  render and of which the result will be stored for future reference.
 * @returns {function} function to call to retrieve the last rendered values.
 */
export function useRenderedValues(selector) {
    const component = Component.current;
    let renderedValues;
    let patchedValues;

    const __render = component.__render.bind(component);
    component.__render = function () {
        renderedValues = selector();
        return __render(...arguments);
    };
    onMounted(onUpdate);
    onPatched(onUpdate);
    function onUpdate() {
        patchedValues = renderedValues;
    }
    return () => patchedValues;
}
