/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

import { Component } from '@odoo/owl';

export class ChannelInvitationFormSelectedPartnerView extends Component {

    /**
     * @returns {ChannelInvitationFormSelectedPartnerView}
     */
    get channelInvitationFormSelectedPartnerView() {
        return this.props.record;
    }

}

Object.assign(ChannelInvitationFormSelectedPartnerView, {
    props: { record: Object },
    template: 'mail.ChannelInvitationFormSelectedPartnerView',
});

registerMessagingComponent(ChannelInvitationFormSelectedPartnerView);
