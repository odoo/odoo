/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            loadMoreAsc
        [Element/model]
            MessageListComponent
        [web.Element/tag]
            t
        [Element/isPresent]
            @record
            .{MessageListComponent/messageListView}
            .{MessageListView/threadViewOwner}
            .{ThreadView/threadCache}
            .{ThreadCache/hasLoadingFailed}
            .{isFalsy}
            .{&}
                @record
                .{MessageListComponent/messageListView}
                .{MessageListView/threadViewOwner}
                .{ThreadView/order}
                .{=}
                    asc
            .{&}
                @record
                .{MessageListComponent/messageListView}
                .{MessageListView/threadViewOwner}
                .{ThreadView/messageViews}
                .{Collection/length}
                .{>}
                    0
`;
