/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class ThreadView extends Component {

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {ThreadView}
     */
    get threadView() {
        return this.messaging && this.messaging.models['ThreadView'].get(this.props.localId);
    }

}

Object.assign(ThreadView, {
    props: { localId: String },
    template: 'mail.ThreadView',
});

registerMessagingComponent(ThreadView);
