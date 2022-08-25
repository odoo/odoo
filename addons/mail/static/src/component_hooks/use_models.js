/** @odoo-module **/

import { Listener } from '@mail/model/model_listener';

const { onRendered, onWillDestroy, onWillRender, useComponent } = owl;

/**
 * This hook provides support for automatically re-rendering when used records
 * or fields changed.
 *
 * Components that use this hook must be instantiated after messaging service is
 * started. However there is no restriction on the messaging record (coming from
 * the modelManager of the messaging service) being already initialized or even
 * created.
 */
export function useModels() {
    const component = useComponent();
    const listener = new Listener({
        isLocking: false, // unfortunately __render has side effects such as children components updating their reference to their corresponding model
        name: `useModels() of ${component}`,
        onChange: () => component.render(),
    });
    onWillRender(() => {
        component.env.services.messaging.modelManager.startListening(listener);
    });
    onRendered(() => {
        component.env.services.messaging.modelManager.stopListening(listener);
    });
    onWillDestroy(() => {
        component.env.services.messaging.modelManager.removeListener(listener);
    });
    component.env.services.messaging.modelManager.messagingCreatedPromise.then(() => {
        component.render();
    });
}
