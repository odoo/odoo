/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            ThreadViewTopbar/onClickInviteButton
        [Action/params]
            record
                [type]
                    ThreadViewTopbar
        [Action/behavior]
            {if}
                @record
                .{ThreadViewTopbar/invitePopoverView}
            .{then}
                {Record/update}
                    [0]
                        @record
                    [1]
                        [ThreadViewTopbar/invitePopoverView]
                            {Record/empty}
            .{else}
                {ThreadViewTopbar/openInvitePopoverView}
                    @record
`;
