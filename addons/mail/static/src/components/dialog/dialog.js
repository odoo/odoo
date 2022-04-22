/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class Dialog extends Component {

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {Dialog}
     */
    get dialog() {
        return this.messaging && this.messaging.models['Dialog'].get(this.props.localId);
    }

}

Object.assign(Dialog, {
    props: { localId: String },
    template: 'mail.Dialog',
});

registerMessagingComponent(Dialog);
