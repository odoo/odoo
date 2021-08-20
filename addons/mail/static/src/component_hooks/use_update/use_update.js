/** @odoo-module **/

import { Listener } from '@mail/model/model_listener';

const { onMounted, onPatched, useComponent } = owl.hooks;

/**
 * This hook provides support for executing code after update (render or patch).
 *
 * @param {Object} param0
 * @param {function} param0.func the function to execute after the update.
 */
export function useUpdate({ func }) {
    const component = useComponent();
    const { modelManager } = component.env.services.messaging;
    const listener = new Listener({
        onChange: () => component.render(),
    });
    function onUpdate() {
        modelManager.startListening(listener);
        func();
        modelManager.stopListening(listener);
    }
    onMounted(onUpdate);
    onPatched(onUpdate);
    const __destroy = component.__destroy;
    component.__destroy = parent => {
        modelManager.removeListener(listener);
        __destroy.call(component, parent);
    };
}
