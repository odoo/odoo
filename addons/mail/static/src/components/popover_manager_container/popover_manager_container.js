/** @odoo-module **/

import { useModels } from '@mail/component_hooks/use_models';
// ensure components are registered beforehand.
import '@mail/components/popover_manager/popover_manager';
import { getMessagingComponent } from "@mail/utils/messaging_component";

const { Component } = owl;

export class PopoverManagerContainer extends Component {

    /**
     * @override
     */
    setup() {
        useModels();
        super.setup();
    }

    get messaging() {
        return this.env.services.messaging.modelManager.messaging;
    }
}

Object.assign(PopoverManagerContainer, {
    components: { PopoverManager: getMessagingComponent('PopoverManager') },
    template: 'mail.PopoverManagerContainer',
});
