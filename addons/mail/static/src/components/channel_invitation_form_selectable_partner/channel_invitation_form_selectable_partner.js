/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class ChannelInvitationFormSelectablePartner extends Component {

    /**
     * @returns {ChannelInvitationForm}
     */
    get channelInvitationForm() {
        return this.messaging && this.messaging.models['ChannelInvitationForm'].get(this.props.channelInvitationFormLocalId);
    }

    /**
     * @returns {Partner}
     */
    get selectablePartner() {
        return this.messaging && this.messaging.models['Partner'].get(this.props.selectablePartnerLocalId);
    }

}

Object.assign(ChannelInvitationFormSelectablePartner, {
    props: {
        channelInvitationFormLocalId: String,
        selectablePartnerLocalId: String,
    },
    template: 'mail.ChannelInvitationFormSelectablePartner',
});

registerMessagingComponent(ChannelInvitationFormSelectablePartner);
