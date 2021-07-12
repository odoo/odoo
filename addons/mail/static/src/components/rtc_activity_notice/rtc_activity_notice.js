/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class RtcActivityNotice extends Component {

    //--------------------------------------------------------------------------
    // Getters / Setters
    //--------------------------------------------------------------------------

    /**
     * @returns {mail.thread|undefined}
     */
    get thread() {
        return this.messaging && this.messaging.mailRtc.channel;
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClick(ev) {
        this.thread.open();
    }

}

Object.assign(RtcActivityNotice, {
    props: {},
    template: 'mail.RtcActivityNotice',
});

registerMessagingComponent(RtcActivityNotice);
