/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            invitationLinkTitle
        [Element/model]
            ChannelInvitationFormComponent
        [Element/isPresent]
            @record
            .{ChannelInvitationFormComponent/channelInvitationForm}
            .{ChannelInvitationForm/thread}
            .{&}
                @record
                .{ChannelInvitationFormComponent/channelInvitationForm}
                .{ChannelInvitationForm/thread}
                .{Thread/invitationLink}
        [web.Element/tag]
            h4
        [web.Element/class]
            mx-3
            mt-3
            mb-2
        [web.Element/textContent]
            {Locale/text}
                Invitation Link
`;
