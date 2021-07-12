/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class RtcInvitations extends Component {

    //--------------------------------------------------------------------------
    // Getters / Setters
    //--------------------------------------------------------------------------

    /**
     * @returns {mail.thread[]}
     */
    get threads() {
        return this.messaging && this.messaging.ringingThreads;
    }

}

Object.assign(RtcInvitations, {
    props: {},
    template: 'mail.RtcInvitations',
});

registerMessagingComponent(RtcInvitations);
