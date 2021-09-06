/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class RtcInvitationCard extends Component {

    //--------------------------------------------------------------------------
    // Getters / Setters
    //--------------------------------------------------------------------------

    /**
     * @returns {mail.thread}
     */
    get thread() {
        return this.messaging.models['mail.thread'].get(this.props.threadLocalId);
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {MouseEvent} ev
     */
    async _onClickAccept(ev) {
        this.thread.open();
        if (this.thread.hasPendingRtcRequest) {
            return;
        }
        await this.thread.toggleCall();
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickAvatar(ev) {
        this.thread.open();
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickRefuse(ev) {
        if (this.thread.hasPendingRtcRequest) {
            return;
        }
        this.thread.leaveCall();
    }

}

Object.assign(RtcInvitationCard, {
    props: {
        threadLocalId: String,
    },
    template: 'mail.RtcInvitationCard',
});

registerMessagingComponent(RtcInvitationCard);
