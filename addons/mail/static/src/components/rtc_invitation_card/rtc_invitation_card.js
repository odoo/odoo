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
        return this.props.record;
    }

}

Object.assign(RtcInvitationCard, {
    props: { record: Object },
    template: 'mail.RtcInvitationCard',
});

registerMessagingComponent(RtcInvitationCard);
