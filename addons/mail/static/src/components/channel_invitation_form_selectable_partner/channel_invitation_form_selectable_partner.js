/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class ChannelInvitationFormSelectablePartner extends Component {

    /**
     * @returns {ChannelInvitationFormSelectablePartnerView}
     */
    get channelInvitationFormSelectablePartnerView() {
        return this.props.record;
    }

}

Object.assign(ChannelInvitationFormSelectablePartner, {
    props: { record: Object },
    template: 'mail.ChannelInvitationFormSelectablePartner',
});

registerMessagingComponent(ChannelInvitationFormSelectablePartner);
