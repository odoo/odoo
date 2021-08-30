/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            MessageListComponent/_adjustScrollFromModel
        [Action/params]
            record
                [type]
                    MessageListComponent
        [Action/behavior]
            {if}
                {MessageListComponent/_getScrollableElement}
                    @record
                .{isFalsy}
                .{|}
                    @record
                    .{MessageListComponent/hasScrollAdjust}
                    .{isFalsy}
            .{then}
                {break}
            {if}
                @record
                .{MessageListComponent/messageListView}
                .{MessageListView/threadViewOwner}
                .{ThreadView/threadCacheInitialScrollHeight}
                .{!=}
                    undefined
                .{&}
                    {MessageListComponent/_getScrollableElement}
                        @record
                    .{web.Element/scrollHeight}
                    .{=}
                        @record
                        .{MessageListComponent/messageListView}
                        .{MessageListView/threadViewOwner}
                        .{ThreadView/threadCacheInitialScrollHeight}
            .{then}
                {MessageListComponent/setScrollTop}
                    [0]
                        @record
                    [1]
                        @record
                        .{MessageListComponent/messageListView}
                        .{MessageListView/threadViewOwner}
                        .{ThreadView/threadCacheInitialScrollPosition}
            .{else}
                {MessageListComponent/_scrollToEnd}
                    @record
`;
