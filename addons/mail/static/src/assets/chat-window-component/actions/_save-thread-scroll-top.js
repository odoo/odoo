/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Save the scroll positions of the chat window in the store.
        This is useful in order to remount chat windows and keep previous
        scroll positions. This is necessary because when toggling on/off
        home menu, the chat windows have to be remade from scratch.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            ChatWindowComponent/_saveThreadScrollTop
        [Action/params]
            record
        [Action/behavior]
            {if}
                @record
                .{ChatWindowComponent/chatWindow}
                .{isFalsy}
                .{|}
                    @record
                    .{ChatWindowComponent/chatWindow}
                    .{ChatWindow/threadView}
                    .{isFalsy}
                .{|}
                    @record
                    .{ChatWindowComponent/chatWindow}
                    .{ChatWindow/threadView}
                    .{ThreadView/messageListView}
                    .{isFalsy}
                .{|}
                    @record
                    .{ChatWindowComponent/chatWindow}
                    .{ChatWindow/threadView}
                    .{ThreadView/messageListView}
                    .{MessageListView/component}
                    .{isFalsy}
                .{|}
                    @record
                    .{ChatWindowComponent/chatWindow}
                    .{ChatWindow/threadViewer}
                    .{isFalsy}
            .{then}
                {break}
            {if}
                @record
                .{ChatWindowComponent/chatWindow}
                .{ChatWindow/threadViewer}
                .{ThreadViewer/threadView}
                .{&}
                    @record
                    .{ChatWindowComponent/chatWindow}
                    .{ChatWindow/threadViewer}
                    .{ThreadViewer/threadView}
                    .{ThreadView/componentHintList}
                    .{Collection/length}
                    .{>}
                        0
            .{then}
                {Dev/comment}
                    the current scroll position is likely incorrect due to
                    the presence of hints to adjust it
                {break}
            {ThreadViewer/saveThreadCacheScrollHeightAsInitial}
                [0]
                    @record
                    .{ChatWindowComponent/chatWindow}
                    .{ChatWindow/threadViewer}
                [1]
                    {MessageListComponent/getScrollHeight}
                        @record
                        .{ChatWindowComponent/chatWindow}
                        .{ChatWindow/threadView}
                        .{ThreadView/messageListView}
                        .{MessageListView/component}
            {ThreadViewer/saveThreadCacheScrollPositionsAsInitial}
                [0]
                    @record
                    .{ChatWindowComponent/chatWindow}
                    .{ChatWindow/threadViewer}
                [1]
                    {MessageListComponent/getScrollTop}
                        @record
                        .{ChatWindowComponent/chatWindow}
                        .{ChatWindow/threadView}
                        .{ThreadView/messageListView}
                        .{MessageListView/component}
`;
