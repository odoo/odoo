/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class RtcInvitationCard extends Component {

    //--------------------------------------------------------------------------
    // Getters / Setters
    //--------------------------------------------------------------------------

    /**
     * @returns {RtcInvitationCard|undefined}
     */
    get rtcInvitationCard() {
        return this.messaging.models['RtcInvitationCard'].get(this.props.localId);
    }

}

Object.assign(RtcInvitationCard, {
    props: { localId: String },
    template: 'mail.RtcInvitationCard',
});

registerMessagingComponent(RtcInvitationCard);
