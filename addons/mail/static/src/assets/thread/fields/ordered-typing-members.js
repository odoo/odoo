/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Ordered typing members on this thread. Lower index means this member
        is currently typing for the longest time. This list includes current
        partner as typer.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            orderedTypingMembers
        [Field/model]
            Thread
        [Field/type]
            many
        [Field/target]
            Partner
        [Field/compute]
            @record
            .{Thread/orderedTypingMemberLocalIds}
            .{Collection/map}
                {Record/insert}
                    [Record/models]
                        Function
                    [Function/in]
                        item
                    [Function/out]
                        {Record/get}
                            @item
            .{Collection/filter}
                {Record/insert}
                    [Record/models]
                        Function
                    [Function/in]
                        item
                    [Function/out]
                        @item
                        .{isTruthy}
`;
