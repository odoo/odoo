/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

import { Component } from '@odoo/owl';

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
