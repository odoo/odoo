/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            WelcomeView/_handleFocus
        [Action/params]
            record
                [type]
                    WelcomeView
        [Action/behavior]
            {if}
                @record
                .{WelcomeView/isDoFocusGuestNameInput}
            .{then}
                {if}
                    @record
                    .{WelcomeView/guestNameInputRef}
                    .{isFalsy}
                .{then}
                    {break}
                {Record/update}
                    [0]
                        @record
                    [1]
                        [WelcomeView/isDoFocusGuestNameInput]
                            false
                {UI/focus}
                    @record
                    .{WelcomeView/guestNameInputRef}
                {Dev/comment}
                    place cursor at end of text
                :length
                    @record
                    .{WelcomeView/pendingGuestName}
                {UI/setSelectionRange}
                    [0]
                        @record
                        .{WelcomeView/guestNameInputRef}
                    [1]
                        @length
                    [2]
                        @length
`;
