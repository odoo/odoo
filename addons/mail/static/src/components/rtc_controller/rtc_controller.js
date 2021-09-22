/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class RtcController extends Component {

    //--------------------------------------------------------------------------
    // Getters / Setters
    //--------------------------------------------------------------------------

    /**
     * @returns {mail.rtc_controller}
     */
    get rtcController() {
        return this.messaging && this.messaging.models['mail.rtc_controller'].get(this.props.localId);
    }

}

Object.assign(RtcController, {
    props: {
        localId: {
            type: String,
        },
    },
    template: 'mail.RtcController',
});

registerMessagingComponent(RtcController);
