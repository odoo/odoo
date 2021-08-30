/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Ordered list of messages linked to this cache.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            orderedMessages
        [Field/model]
            ThreadCache
        [Field/type]
            many
        [Field/target]
            Message
        [Field/compute]
            @record
            .{ThreadCache/messages}
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
`;
