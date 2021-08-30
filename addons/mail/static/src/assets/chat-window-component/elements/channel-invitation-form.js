/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            channelInvitationForm
        [Element/model]
            ChatWindowComponent
        [Field/target]
            ChannelInvitationFormComponent
        [Element/isPresent]
            @record
            .{ChatWindowComponent/chatWindow}
            .{ChatWindow/channelInvitationForm}
        [ChannelInvitationFormComponent/channelInvitationForm]
            @record
            .{ChatWindowComponent/channelInvitationForm}
        [web.Element/style]
            [web.scss/min-height]
                450
                px
                {Dev/comment}
                    allow flex shrink smaller than content (but not too small)
`;
