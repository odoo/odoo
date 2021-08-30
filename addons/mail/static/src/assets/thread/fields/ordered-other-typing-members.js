/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Ordered typing members on this thread, excluding the current partner.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            orderedOtherTypingMembers
        [Field/model]
            Thread
        [Field/type]
            many
        [Field/target]
            Partner
        [Field/compute]
            @record
            .{Thread/orderedTypingMembers}
            .{Collection/filter}
                {Record/insert}
                    [Record/models]
                        Function
                    [Function/in]
                        item
                    [Function/out]
                        @item
                        .{!=}
                            {Env/currentPartner}
`;
