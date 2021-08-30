/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            MessageListComponent/getOrderedMessages
        [Action/params]
            record
                [type]
                    MessageListComponent
        [Action/returns]
            Collection<Message>
        [Action/behavior]
            :threadCache
                @record
                .{MessageListComponent/messageListView}
                .{MessageListView/threadViewOwner}
                .{ThreadView/threadCache}
            {if}
                @record
                .{MessageListComponent/order}
                .{=}
                    desc
            .{then}
                    @threadCache
                    .{ThreadCache/orderedMessages}
                    .{Collection/reverse}
            .{else}
                @threadCache
                .{ThreadCache/orderedMessages}
`;
