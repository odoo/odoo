/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class RtcActivityNotice extends Component {

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClick(ev) {
        this.messaging.rtc.channel.open();
    }

}

Object.assign(RtcActivityNotice, {
    props: {},
    template: 'mail.RtcActivityNotice',
});

registerMessagingComponent(RtcActivityNotice);
