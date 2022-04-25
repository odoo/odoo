/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class ChannelInvitationFormSelectedPartner extends Component {

    /**
     * @returns {ChannelInvitationForm}
     */
    get channelInvitationForm() {
        return this.messaging && this.messaging.models['ChannelInvitationForm'].get(this.props.channelInvitationFormLocalId);
    }

    /**
     * @returns {Partner}
     */
    get selectedPartner() {
        return this.messaging && this.messaging.models['Partner'].get(this.props.selectedPartnerLocalId);
    }

}

Object.assign(ChannelInvitationFormSelectedPartner, {
    props: {
        channelInvitationFormLocalId: String,
        selectedPartnerLocalId: String,
    },
    template: 'mail.ChannelInvitationFormSelectedPartner',
});

registerMessagingComponent(ChannelInvitationFormSelectedPartner);
