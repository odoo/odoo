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
        isLocking: false, // unfortunately __render has side effects such as children components updating their reference to their corresponding model
        name: `useModels() of ${component}`,
        onChange: () => component.render(),
    });
    const __render = component.__render;
    component.__render = fiber => {
        if (modelManager) {
            modelManager.startListening(listener);
        }
        __render.call(component, fiber);
        if (modelManager) {
            modelManager.stopListening(listener);
        }
    };
    const __destroy = component.__destroy;
    component.__destroy = parent => {
        if (modelManager) {
            modelManager.removeListener(listener);
        }
        __destroy.call(component, parent);
    };
    modelManager.messagingCreatedPromise.then(() => {
        component.render();
    });
}
