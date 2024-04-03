/** @odoo-module **/

import { useModels } from '@mail/component_hooks/use_models';
// ensure components are registered beforehand.
import '@mail/components/call_systray_menu/call_systray_menu';
import { getMessagingComponent } from "@mail/utils/messaging_component";

const { Component } = owl;

export class CallSystrayMenuContainer extends Component {

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

Object.assign(CallSystrayMenuContainer, {
    components: { CallSystrayMenu: getMessagingComponent('CallSystrayMenu') },
    template: 'mail.CallSystrayMenuContainer',
});
