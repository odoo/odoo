/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

import Dialog from 'web.OwlDialog';

const { Component } = owl;
const { useRef } = owl.hooks;

export class DeleteMessageConfirmDialog extends Component {

    /**
     * @override
     */
    setup() {
        super.setup();
        this.title = this.env._t("Confirmation");
        this.dialogRef = useRef('dialog');
    }

    /**
     * @returns {mail.message}
     */
    get actionList() {
        return this.messaging && this.messaging.models['mail.message_action_list'].get(this.props.actionListLocalId);
    }
}

Object.assign(DeleteMessageConfirmDialog, {
    components: {
        Dialog,
    },
    props: {
        actionListLocalId: String,
    },
    template: 'mail.DeleteMessageConfirmDialog',
});

registerMessagingComponent(DeleteMessageConfirmDialog);
