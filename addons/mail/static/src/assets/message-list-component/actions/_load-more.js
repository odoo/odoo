/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            MessageListComponent/_loadMore
        [Action/params]
            record
                [type]
                    MessageListComponent
        [Action/behavior]
            {if}
                @record
                .{MessageListComponent/messageListView}
                .{MessageListView/threadViewOwner}
                .{ThreadView/threadCache}
                .{isFalsy}
            .{then}
                {break}
            {ThreadCache/loadMoreMessages}
                @record
                .{MessageListComponent/messageListView}
                .{MessageListView/threadViewOwner}
                .{ThreadView/threadCache}
`;
