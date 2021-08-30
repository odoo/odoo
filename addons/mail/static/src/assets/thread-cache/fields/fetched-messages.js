/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        List of messages that have been fetched by this cache.

        This DOES NOT necessarily includes all messages linked to this thread
        cache (@see messages field for that): it just contains list
        of successive messages that have been explicitly fetched by this
        cache. For all non-main caches, this corresponds to all messages.
        For the main cache, however, messages received from longpolling
        should be displayed on main cache but they have not been explicitly
        fetched by cache, so they ARE NOT in this list (at least, not until a
        fetch on this thread cache contains this message).

        The distinction between messages and fetched messages is important
        to manage "holes" in message list, while still allowing to display
        new messages on main cache of thread in real-time.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            fetchedMessages
        [Field/model]
            ThreadCache
        [Field/type]
            many
        [Field/target]
            Message
        [Field/compute]
            {Dev/comment}
                Adjust with messages unlinked from thread
            {if}
                @record
                .{ThreadCache/thread}
                .{isFalsy}
            .{then}
                {Record/empty}
                {break}
            :toUnlinkMessages
                {Record/insert}
                    [Record/models]
                        Collection
            {foreach}
                @record
                .{ThreadCache/fetchedMessages}
            .{as}
                message
            .{do}
                {if}
                    @record
                    .{ThreadCache/thread}
                    .{Thread/messages}
                    .{Collection/includes}
                        @message
                    .{isFalsy}
                .{then}
                    {Collection/push}
                        @toUnlinkMessages
                        @message
            {Field/remove}
                @toUnlinkMessages
`;
