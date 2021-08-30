/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            MessageListComponent/_isLoadMoreVisible
        [Action/params]
            record
                [type]
                    MessageListComponent
        [Action/returns]
            Boolean
        [Action/behavior]
            :loadMore
                @record
                .{MessageListComponent/loadMore}
            {if}
                @loadMore
                .{isFalsy}
            .{then}
                false;
            .{else}
                :loadMoreRect
                    @loadMore
                    .{web.Element/getBoundingClientRect}
                :elRect
                    {MessageListComponent/_getScrollableElement}
                        @record
                    .{web.Element/getBoundingClientRect}
                :isInvisible
                    @loadMoreRect
                    .{web.Element/top}
                    .{>}
                        @elRect
                        .{web.Element/bottom}
                    .{|}
                        @loadMoreRect
                        .{web.Element/bottom}
                        .{<}
                            @elRect
                            .{web.Element/top}
                @isInvisible
                .{isFalsy}
`;
