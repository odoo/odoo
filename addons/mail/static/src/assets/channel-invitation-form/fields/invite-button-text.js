/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determines the text of the invite button.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            inviteButtonText
        [Field/model]
            ChannelInvitationForm
        [Field/type]
            attr
        [Field/target]
            String
        [Field/compute]
            {if}
                @record
                .{ChannelInvitationForm/thread}
                .{isFalsy}
            .{then}
                {Record/empty}
            .{else}
                {switch}
                    @record
                    .{ChannelInvitationForm/thread}
                    .{Thread/channelType}
                .{case}
                    [chat]
                        {Locale/text}
                            Create group chat
                    [group]
                        {Locale/text}
                            Invite to group chat
                    []
                        {Locale/text}
                            Invite to Channel
`;