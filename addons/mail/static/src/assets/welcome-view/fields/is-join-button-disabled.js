/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determines whether the 'joinButton' is disabled.

        Shall be disabled when 'pendingGuestName' is an empty string while
        the current user is a guest.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            isJoinButtonDisabled
        [Field/model]
            WelcomeView
        [Field/type]
            attr
        [Field/target]
            Boolean
        [Field/compute]
            {if}
                {Env/currentGuest}
                .{isFalsy}
            .{then}
                false
            .{elif}
                {Env/pendingGuestName}
                .{String/trim}
                .{String/length}
                .{>}
                    0
            .{then}
                false
            .{else}
                true
`;
