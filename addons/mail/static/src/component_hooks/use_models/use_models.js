/** @odoo-module **/

import { Listener } from '@mail/model/model_listener';

const { useComponent } = owl.hooks;

/**
 * This hook provides support for automatically re-rendering when used records
 * or fields changed.
 */
export function useModels() {
    const component = useComponent();
    const { modelManager } = component.env.services.messaging;
    const listener = new Listener({
        onChange: () => component.render(),
    });
    const __render = component.__render;
    component.__render = fiber => {
        modelManager.startListening(listener);
        __render.call(component, fiber);
        modelManager.stopListening(listener);
    };
    const __destroy = component.__destroy;
    component.__destroy = parent => {
        modelManager.removeListener(listener);
        __destroy.call(component, parent);
    };
    modelManager.messagingCreatedPromise.then(() => {
        component.render();
    });
}
