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

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {MouseEvent} ev
     */
    async _onClickAccept(ev) {
        this.rtcInvitationCard.thread.open();
        if (this.rtcInvitationCard.thread.hasPendingRtcRequest) {
            return;
        }
        await this.rtcInvitationCard.thread.toggleCall();
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickAvatar(ev) {
        this.rtcInvitationCard.thread.open();
    }

}

Object.assign(RtcInvitationCard, {
    props: { localId: String },
    template: 'mail.RtcInvitationCard',
});

registerMessagingComponent(RtcInvitationCard);
