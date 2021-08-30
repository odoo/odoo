/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            noSelectablePartner
        [Element/model]
            ChannelInvitationFormComponent
        [Element/isPresent]
            @record
            .{ChannelInvitationFormComponent/channelInvitationForm}
            .{ChannelInvitationForm/selectablePartners}
            .{Collection/length}
            .{=}
                0
        [web.Element/class]
            mx-3
        [web.Element/textContent]
            {Locale/text}
                No user found that is not already a member of this channel.
`;
