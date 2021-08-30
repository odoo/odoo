/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            ThreadViewTopbar/_applyGuestRename
        [Action/params]
            record
                [type]
                    ThreadViewTopbar
        [Action/behavior]
            {if}
                @record
                .{ThreadViewTopbar/hasGuestNameChanged}
            .{then}
                {Guest/performRpcGuestUpdateName}
                    [id]
                        {Env/currentGuest}
                        .{Guest/id}
                    [name]
                        @record
                        .{ThreadViewTopbar/pendingGuestName}
                        .{String/trim}
            {ThreadViewTopbar/_resetGuestNameInput}
                @record
`;
