/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class RtcController extends Component {

    /**
     * @returns {RtcController}
     */
    get rtcController() {
        return this.messaging && this.messaging.models['RtcController'].get(this.props.localId);
    }

}

Object.assign(RtcController, {
    props: { localId: String },
    template: 'mail.RtcController',
});

registerMessagingComponent(RtcController);
