/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

import Dialog from 'web.OwlDialog';

const { Component } = owl;

export class DeleteMessageConfirm extends Component {

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
        return this.messaging && this.messaging.models['MessageActionList'].get(this.props.localId);
    }
}

Object.assign(DeleteMessageConfirm, {
    components: {
        Dialog,
    },
    props: {
        localId: String,
    },
    template: 'mail.DeleteMessageConfirm',
});

registerMessagingComponent(DeleteMessageConfirm);
