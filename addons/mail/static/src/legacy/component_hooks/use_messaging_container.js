/** @odoo-module **/

import { useModels } from "@mail/legacy/component_hooks/use_models";
import { componentRegistry, getMessagingComponent } from "@mail/legacy/utils/messaging_component";

import { useComponent } from "@odoo/owl";

export function useMessagingContainer() {
    const component = useComponent();
    component.isLoaded = false;
    useModels();
    component.env.services.messaging.modelManager.messagingCreatedPromise.then(() => {
        const components = { ...component.constructor.components };
        for (const name in componentRegistry) {
            Object.assign(components, { [name]: getMessagingComponent(name) });
        }
        component.constructor.components = components;
        component.isLoaded = true;
        component.render();
    });
}
