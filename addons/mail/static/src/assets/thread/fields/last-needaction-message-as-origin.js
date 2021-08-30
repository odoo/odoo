/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            lastNeedactionMessageAsOrigin
        [Field/model]
            Thread
        [Field/type]
            one
        [Field/target]
            Message
        [Field/compute]
            :orderedNeedactionMessagesAsOriginThread
                @record
                .{Thread/needactionMessagesAsOriginThread}
                .{Collection/sort}
                    {Record/insert}
                        [Record/models]
                            Function
                        [Function/in]
                            item1
                            item2
                        [Function/out]
                            {if}
                                @item1
                                .{Message/id}
                                .{<}
                                    @item2
                                    .{Message/id}
                            .{then}
                                -1
                            .{else}
                                1
            {if}
                @orderedNeedactionMessagesAsOriginThread
                .{Collection/length}
                .{>}
                    0
            .{then}
                @orderedNeedactionMessagesAsOriginThread
                .{Collection/last}
            .{else}
                {Record/empty}
`;
