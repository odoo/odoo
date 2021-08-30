/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Last message that has been fetched by this thread cache.

        This DOES NOT necessarily mean the last message linked to this thread
        cache (@see lastMessage field for that). @see fetchedMessages field
        for a deeper explanation about "fetched" messages.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            lastFetchedMessage
        [Field/model]
            ThreadCache
        [Field/type]
            one
        [Field/target]
            Message
        [Field/compute]
            {if}
                @record
                .{ThreadCache/orderedFetchedMessages}
                .{Collection/last}
                .{isFalsy}
            .{then}
                {Record/empty}
            .{else}
                @record
                .{ThreadCache/orderedFetchedMessages}
                .{Collection/last}
`;
