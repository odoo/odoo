/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class ChannelInvitationFormSelectablePartner extends Component {

    /**
     * @returns {ChannelInvitationForm}
     */
    get channelInvitationForm() {
        return this.props.channelInvitationForm;
    }

    /**
     * @returns {Partner}
     */
    get selectablePartner() {
        return this.props.selectablePartner;
    }

}

Object.assign(ChannelInvitationFormSelectablePartner, {
    props: {
        channelInvitationForm: Object,
        selectablePartner: Object,
    },
    template: 'mail.ChannelInvitationFormSelectablePartner',
});

registerMessagingComponent(ChannelInvitationFormSelectablePartner);
