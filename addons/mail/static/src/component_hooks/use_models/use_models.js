/** @odoo-module **/

import { Listener } from '@mail/model/model_listener';

const { useComponent } = owl.hooks;

/**
 * This hook provides support for automatically re-rendering when used records
 * or fields changed.
 */
export function useModels() {
    const component = useComponent();
    const listener = new Listener({
        onChange: () => component.render(),
    });
    const __render = component.__render;
    component.__render = fiber => {
        if (component.env.modelManager) {
            component.env.modelManager.startListening(listener);
        }
        __render.call(component, fiber);
        if (component.env.modelManager) {
            component.env.modelManager.stopListening(listener);
        }
    };
    const __destroy = component.__destroy;
    component.__destroy = parent => {
        if (component.env.modelManager) {
            component.env.modelManager.removeListener(listener);
        }
        __destroy.call(component, parent);
    };
    if (!component.env.messaging) {
        component.env.messagingCreatedPromise.then(() => component.render());
    }
}
