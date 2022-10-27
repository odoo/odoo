/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class ChannelInvitationFormSelectablePartnerView extends Component {

    /**
     * @returns {ChannelInvitationFormSelectablePartnerView}
     */
    get channelInvitationFormSelectablePartnerView() {
        return this.props.record;
    }

}

Object.assign(ChannelInvitationFormSelectablePartnerView, {
    props: { record: Object },
    template: 'mail.ChannelInvitationFormSelectablePartnerView',
});

registerMessagingComponent(ChannelInvitationFormSelectablePartnerView);
