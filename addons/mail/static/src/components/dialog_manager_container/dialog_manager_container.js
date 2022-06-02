/** @odoo-module **/

import { useModels } from '@mail/component_hooks/use_models';
// ensure components are registered beforehand.
import '@mail/components/dialog_manager/dialog_manager';
import { getMessagingComponent } from "@mail/utils/messaging_component";

const { Component } = owl;

export class DialogManagerContainer extends Component {

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

Object.assign(DialogManagerContainer, {
    components: { DialogManager: getMessagingComponent('DialogManager') },
    template: 'mail.DialogManagerContainer',
});
