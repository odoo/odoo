/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Updates guest if needed then displays the thread view instead of the
        welcome view.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            WelcomeView/joinChannel
        [Action/params]
            record
                [type]
                    WelcomeView
        [Action/behavior]
            {if}
                @record
                .{WelcomeView/hasGuestNameChanged}
            .{then}
                {WelcomeView/performRpcGuestUpdateName}
                    @record
                    .{WelcomeView/pendingGuestName}
                    .{String/trim}
            {if}
                @record
                .{WelcomeView/discussPublicView}
                .{DiscussPublicView/shouldAddGuestAsMemberOnJoin}
            .{then}
                {Guest/performRpcGuestUpdateName}
                    [id]
                        {Env/currentGuest}
                        .{Guest/id}
                    [name]
                        @record
                        .{WelcomeView/pendingGuestName}
                        .{String/trim}
            {DiscussPublicView/switchToThreadView}
                @record
                .{WelcomeView/discussPublicView}
`;
