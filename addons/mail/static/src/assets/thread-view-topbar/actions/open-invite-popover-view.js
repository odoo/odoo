/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Open the invite popover view in this thread view topbar.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            ThreadViewTopbar/openInvitePopoverView
        [Action/params]
            record
                [type]
                    ThreadViewTopbar
        [Action/behavior]
            {Record/update}
                [0]
                    @record
                [1]
                    [ThreadViewTopbar/invitePopoverView]
                        {Record/insert}
                            [Record/models]
                                PopoverView
            {if}
                {Env/isCurrentUserGuest}
            .{then}
                {break}
            {Record/update}
                [0]
                    @record
                    .{ThreadViewTopbar/invitePopoverView}
                    .{PopoverView/channelInvitationForm}
                [1]
                    [ChannelInvitationForm/doFocusOnSearchInput]
                        true
            {ChannelInvitationForm/searchPartnersToInvite}
                @record
                .{ThreadViewTopbar/invitePopoverView}
                .{PopoverView/channelInvitationForm}
`;
