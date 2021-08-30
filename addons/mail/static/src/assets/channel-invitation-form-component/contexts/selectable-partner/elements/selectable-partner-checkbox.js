/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            selectablePartnerCheckbox
        [Element/model]
            ChannelInvitationFormComponent:selectablePartner
        [web.Element/tag]
            input
        [web.Element/type]
            checkbox
        [web.Element/class]
            flex-shrink-0
        [web.Element/isChecked]
            @record
            .{ChannelInvitationFormComponent/channelInvitationForm}
            .{ChannelInvitationForm/selectedPartners}
            .{Collection/includes}
                @record
                .{ChannelInvitationFormComponent:selectablePartner/selectablePartner}
        [Element/onInput]
            {ChannelInvitationForm/onInputPartnerCheckbox}
                @record
                .{ChannelInvitationFormComponent/channelInvitationForm}
                @record
                .{ChannelInvitationFormComponent:selectablePartner/selectablePartner}
`;
