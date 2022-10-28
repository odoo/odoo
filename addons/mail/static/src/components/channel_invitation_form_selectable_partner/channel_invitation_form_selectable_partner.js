/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

import { Component } from '@odoo/owl';

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
