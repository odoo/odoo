/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            AutocompleteInputComponent/_hide
        [Action/params]
            record
        [Action/behavior]
            {if}
                @record
                .{AutocompleteInputComponent/onHide}
            .{then}
                {break}
                    @record
                    .{AutocompleteInputComponent/onHide}
                    .{Function/call}
            {if}
                @record
                .{AutocompleteInputComponent/discussComponent}
            .{then}
                {Discuss/clearIsAddingItem}
                    @record
                    .{AutocompleteInputComponent/discussComponent}
                    .{DiscussComponent/discussView}
                    .{DiscussView/discuss}
            {if}
                @record
                .{AutocompleteInputComponent/messagingMenuComponent}
            .{then}
                {MessagingMenu/toggleMobileNewMessage}
                    @record
                    .{AutocompleteInputComponent/messagingMenuComponent}
                    .{MessagingMenuComponent/messagingMenu}
`;
