/** @odoo-module **/

import { Listener } from '@mail/model/model_listener';

const { onMounted, onPatched, onWillDestroy, useComponent } = owl;

/**
 * This hook provides support for executing code after update (render or patch).
 *
 * @param {Object} param0
 * @param {function} param0.func the function to execute after the update.
 */
export function useUpdate({ func }) {
    const component = useComponent();
    const listener = new Listener({
        isLocking: false, // unfortunately onUpdate methods often have side effect
        name: `useUpdate() of ${component}`,
        onChange: () => component.render(),
    });
    function onUpdate() {
        component.env.services.messaging.modelManager.startListening(listener);
        func();
        component.env.services.messaging.modelManager.stopListening(listener);
    }
    onMounted(onUpdate);
    onPatched(onUpdate);
    onWillDestroy(() => {
        component.env.services.messaging.modelManager.removeListener(listener);
    });
}
