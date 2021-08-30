/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        States whether the message list scroll position is at the end of
        the message list. Depending of the message list order, this could be
        the top or the bottom.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            isAtEnd
        [Field/model]
            MessageListView
        [Field/type]
            attr
        [Field/target]
            Boolean
        [Field/compute]
            {Dev/comment}
                The margin that we use to detect that the scrollbar is a the end of
                the threadView.
            :endThreshold
                30
            {if}
                @record
                .{MessageListView/threadViewOwner}
                .{ThreadView/order}
                .{=}
                    asc
            .{then}
                @record
                .{MessageListView/scrollTop}
                .{>=}
                    @record
                    .{MessageListView/scrollHeight}
                    .{-}
                        @record
                        .{MessageListView/clientHeight}
                    .{-}
                        @endThreshold
            .{else}
                @record
                .{MessageListView/scrollTop}
                .{<=}
                    @endThreshold
`;
