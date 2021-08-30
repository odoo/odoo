/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            inviteButton
        [Element/model]
            ChannelInvitationFormComponent
        [web.Element/tag]
            button
        [web.Element/class]
            btn
            btn-primary
            w-100
        [web.Element/isDisabled]
            @record
            .{ChannelInvitationFormComponent/channelInvitationForm}
            .{ChannelInvitationForm/selectedPartners}
            .{Collection/length}
            .{=}
                0
        [Element/onClick]
            {ChannelInvitationForm/onClickInvite}
                @record
                .{ChannelInvitationFormComponent/channelInvitationForm}
                @ev
        [web.Element/textContent]
            @record
            .{ChannelInvitationFormComponent/channelInvitationForm}
            .{ChannelInvitationForm/inviteButtonText}
`;
