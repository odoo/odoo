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
    }

    /**
     * @returns {MessageActionList}
     */
    get messageActionList() {
        return this.messaging && this.messaging.models['MessageActionList'].get(this.props.messageActionListLocalId);
    }
}

Object.assign(DeleteMessageConfirmDialog, {
    components: {
        Dialog,
    },
    props: {
        messageActionListLocalId: String,
    },
    template: 'mail.DeleteMessageConfirmDialog',
});

registerMessagingComponent(DeleteMessageConfirmDialog);
