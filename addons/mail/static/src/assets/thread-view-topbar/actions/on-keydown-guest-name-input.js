/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Handles keydown on the "guest name" input of this top bar.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            ThreadViewTopbar/onKeyDownGuestNameInput
        [Action/params]
            ev
                [type]
                    web.KeyboardEvent
            record
                [type]
                    ThreadViewTopbar
        [Action/behavior]
            {switch}
                @ev
                .{web.KeyboardEvent/key}
            .{case}
                [Enter]
                    {if}
                        @record
                        .{ThreadViewTopbar/pendingGuestName}
                        .{String/trim}
                        .{String/isEmpty}
                        .{isFalsy}
                    .{then}
                        {ThreadViewTopbar/_applyGuestRename}
                            @record
                [Escape]
                    {ThreadViewTopbar/_resetGuestNameInput}
                        @record
`;
