/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            MessageListComponent/_adjustScrollForExtraMessagesAtTheStart
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
                .{|}
                    @record
                    .{MessageListComponent/_willPatchSnapshot}
                    .{isFalsy}
                .{|}
                    @record
                    .{MessageListComponent/order}
                    .{=}
                        desc
            .{then}
                {break}
            :scrollHeight
                @record
                .{MessageListComponent/_willPatchSnapshot}
                .{Dict/get}
                    scrollHeight
            :scrollTop
                @record
                .{MessageListComponent/_willPatchSnapshot}
                .{Dict/get}
                    scrollTop
            {MessageListComponent/setScrollTop}
                [0]
                    @record
                [1]
                    {MessageListComponent/_getScrollableElement}
                        @record
                    .{web.Element/scrollHeight}
                    .{-}
                        @scrollHeight
                    .{+}
                        @scrollTop
`;
