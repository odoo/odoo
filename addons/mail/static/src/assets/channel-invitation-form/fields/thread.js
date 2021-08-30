/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        States the thread on which this list operates (if any).
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            thread
        [Field/model]
            ChannelInvitationForm
        [Field/type]
            one
        [Field/target]
            Thread
        [Field/isRequired]
            true
        [Field/isReadonly]
            true
        [Field/compute]
            {if}
                @record
                .{ChannelInvitationForm/popoverViewOwner}
                .{&}
                    @record
                    .{ChannelInvitationForm/popoverViewOwner}
                    .{PopoverView/threadViewTopbarOwnerAsInvite}
                .{&}
                    @record
                    .{ChannelInvitationForm/popoverViewOwner}
                    .{PopoverView/threadViewTopbarOwnerAsInvite}
                    .{ThreadViewTopbar/thread}
            .{then}
                @record
                .{ChannelInvitationForm/popoverViewOwner}
                .{PopoverView/threadViewTopbarOwnerAsInvite}
                .{ThreadViewTopbar/thread}
            .{elif}
                @record
                .{ChannelInvitationForm/chatWindow}
                .{&}
                    @record
                    .{ChannelInvitationForm/chatWindow}
                    .{ChatWindow/thread}
            .{then}
                @record
                .{ChannelInvitationForm/chatWindow}
                .{ChatWindow/thread}
            .{else}
                {Record/empty}
`;
