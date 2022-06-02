/** @odoo-module **/

import { Listener } from '@mail/model/model_listener';

const { onMounted, onPatched, onWillDestroy, onWillRender, useComponent } = owl;

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
    const component = useComponent();
    let renderedValues;
    let patchedValues;
    const listener = new Listener({
        name: `useRenderedValues() of ${component}`,
        onChange: () => component.render(),
    });
    onWillRender(() => {
        component.env.services.messaging.modelManager.startListening(listener);
        renderedValues = selector();
        component.env.services.messaging.modelManager.stopListening(listener);
    });
    onMounted(onUpdate);
    onPatched(onUpdate);
    function onUpdate() {
        patchedValues = renderedValues;
    }
    onWillDestroy(() => component.env.services.messaging.modelManager.removeListener(listener));
    return () => patchedValues;
}
