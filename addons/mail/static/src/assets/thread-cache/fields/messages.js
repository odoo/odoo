/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        List of messages linked to this cache.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            messages
        [Field/model]
            ThreadCache
        [Field/type]
            many
        [Field/target]
            Message
        [Field/compute]
            {if}
                @record
                .{ThreadCache/thread}
                .{isFalsy}
            .{then}
                {Record/empty}
                {break}
            :newerMessages
                {if}
                    @record
                    .{ThreadCache/lastFetchedMessage}
                    .{isFalsy}
                .{then}
                    @record
                    .{ThreadCache/thread}
                    .{Thread/messages}
                .{else}
                    @record
                    .{ThreadCache/thread}
                    .{Thread/messages}
                    .{Collection/filter}
                        {Record/insert}
                            [Record/models]
                                Function
                            [Function/in]
                                item
                            [Function/out]
                                @item
                                .{Message/id}
                                .{>}
                                    @record
                                    .{ThreadCache/lastFetchedMessage}
                                    .{Message/id}
            @record
            .{ThreadCache/fetchedMessages}
            .{Collection/concat}
                @newerMessages
`;
