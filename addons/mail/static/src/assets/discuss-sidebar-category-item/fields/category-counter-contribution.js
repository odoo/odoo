/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determines the contribution of this discuss sidebar category item to
        the counter of this category.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            categoryCounterContribution
        [Field/model]
            DiscussSidebarCategoryItem
        [Field/type]
            attr
        [Field/target]
            Integer
        [Field/isReadonly]
            true
        [Field/compute]
            {switch}
                @record
                .{DiscussSidebarCategoryItem/channel}
                .{Thread/channelType}
            .{case}
                [channel]
                    {if}
                        @record
                        .{DiscussSidebarCategoryItem/channel}
                        .{Thread/messageNeedactionCounter}
                        .{>}
                            0
                    .{then}
                        1
                    .{else}
                        0
                [chat]
                    {if}
                        @record
                        .{DiscussSidebarCategoryItem/channel}
                        .{Thread/localMessageUnreadCounter}
                        .{>}
                            0
                    .{then}
                        1
                    .{else}
                        0
                [group]
                    {if}
                        @record
                        .{DiscussSidebarCategoryItem/channel}
                        .{Thread/localMessageUnreadCounter}
                        .{>}
                            0
                    .{then}
                        1
                    .{else}
                        0
`;
