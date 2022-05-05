/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class ChannelInvitationFormSelectedPartner extends Component {

    /**
     * @returns {ChannelInvitationFormSelectedPartnerView}
     */
    get channelInvitationFormSelectedPartnerView() {
        return this.props.record;
    }

}

Object.assign(ChannelInvitationFormSelectedPartner, {
    props: { record: Object },
    template: 'mail.ChannelInvitationFormSelectedPartner',
});

registerMessagingComponent(ChannelInvitationFormSelectedPartner);
