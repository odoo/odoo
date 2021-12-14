/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class RtcController extends Component {

    //--------------------------------------------------------------------------
    // Getters / Setters
    //--------------------------------------------------------------------------

    /**
     * @returns {RtcController}
     */
    get rtcController() {
        return this.messaging && this.messaging.models['RtcController'].get(this.props.localId);
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
