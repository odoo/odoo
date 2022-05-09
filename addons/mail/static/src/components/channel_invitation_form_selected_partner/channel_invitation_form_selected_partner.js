/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class ChannelInvitationFormSelectedPartner extends Component {

    /**
     * @returns {ChannelInvitationForm}
     */
    get channelInvitationForm() {
        return this.props.channelInvitationForm;
    }

    /**
     * @returns {Partner}
     */
    get selectedPartner() {
        return this.props.selectedPartner;
    }

}

Object.assign(ChannelInvitationFormSelectedPartner, {
    props: {
        channelInvitationForm: Object,
        selectedPartner: Object,
    },
    template: 'mail.ChannelInvitationFormSelectedPartner',
});

registerMessagingComponent(ChannelInvitationFormSelectedPartner);
