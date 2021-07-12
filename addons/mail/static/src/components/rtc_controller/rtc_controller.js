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

    /**
     * @returns {mail.thread}
     */
    get rtcSession() {
        return this.messaging && this.messaging.mailRtc.currentRtcSession;
    }

    /**
     * @returns {mail.thread|undefined}
     */
    get thread() {
        return this.rtcController && this.rtcController.callViewer.threadView.thread;
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
