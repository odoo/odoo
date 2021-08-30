/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            loadMore
        [Element/model]
            MessageListComponent
        [web.Element/tag]
            a
        [Record/models]
            MessageListComponent/item
        [Element/isPresent]
            @record
            .{MessageListComponent/messageListView}
            .{MessageListView/threadViewOwner}
            .{ThreadView/threadCache}
            .{ThreadCache/isLoadingMore}
            .{isFalsy}
            .{&}
                @record
                .{MessageListComponent/messageListView}
                .{MessageListView/threadViewOwner}
                .{ThreadView/threadCache}
                .{ThreadCache/isAllHistoryLoaded}
                .{isFalsy}
            .{&}
                @record
                .{MessageListComponent/messageListView}
                .{MessageListView/threadViewOwner}
                .{ThreadView/thread}
                .{Thread/isTemporary}
                .{isFalsy}
        [web.Element/href]
            #
        [Element/onClick]
            {web.Event/preventDefault}
                @ev
            {MessageListComponent/_loadMore}
                @record
        [web.Element/textContent]
            {Locale/text}
                Load more
        [web.Element/style]
            [web.scss/align-self]
                center
            [web.scss/cursor]
                pointer
`;
