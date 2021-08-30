/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        The record that represents the content inside the popover view.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            channelInvitationForm
        [Field/model]
            PopoverView
        [Field/type]
            one
        [Field/target]
            ChannelInvitationForm
        [Field/isCausal]
            true
        [Field/isReadonly]
            true
        [Field/inverse]
            ChannelInvitationForm/popoverViewOwner
        [Field/compute]
            {if}
                @record
                .{PopoverView/threadViewTopbarOwnerAsInvite}
            .{then}
                {Record/insert}
                    [Record/models]
                        ChannelInvitationForm
            .{else}
                {Record/empty}
`;
