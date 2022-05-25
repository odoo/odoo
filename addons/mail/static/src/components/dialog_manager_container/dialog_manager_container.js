/** @odoo-module **/

import { useModels } from '@mail/component_hooks/use_models';
// ensure components are registered beforehand.
import '@mail/components/dialog_manager/dialog_manager';
import { getMessagingComponent } from "@mail/utils/messaging_component";

const { Component, useSubEnv } = owl;

export class DialogManagerContainer extends Component {

    /**
     * @override
     */
    setup() {
        // for now, the legacy env is needed for internal functions such as
        // `useModels` to work
        useSubEnv(Component.env);
        useModels();
        super.setup();
    }
}

Object.assign(DialogManagerContainer, {
    components: { DialogManager: getMessagingComponent('DialogManager') },
    template: 'mail.DialogManagerContainer',
});
