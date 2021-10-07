/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class RtcActivityNotice extends Component {

    setup() {
        // for now, the legacy env is needed for internal functions such as
        // `useModels` to work
        this.env = owl.Component.env;
    }

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
