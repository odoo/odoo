/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        All messages ordered like they are displayed.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            orderedMessages
        [Field/model]
            Thread
        [Field/type]
            many
        [Field/target]
            Message
        [Field/compute]
            @record
            .{Thread/messages}
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
