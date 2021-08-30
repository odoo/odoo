/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determines the discuss sidebar category items that are displayed by
        this discuss sidebar category.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            categoryItems
        [Field/model]
            DiscussSidebarCategory
        [Field/type]
            many
        [Field/target]
            DiscussSidebarCategoryItem
        [Field/isCausal]
            true
        [Field/inverse]
            DiscussSidebarCategoryItem/category
        [Field/sort]
            {switch}
                @record
                .{DiscussSidebarCategory/sortComputeMethod}
            .{case}
                [name]
                    defined-first
                        DiscussSidebarCategory/channel
                    defined-first
                        DiscussSidebarCategory/channel
                        Thread/displayName
                    case-insensitive-asc
                        DiscussSidebarCategory/channel
                        Thread/displayName
                    smaller-first
                        DiscussSidebarCategory/channel
                        Thread/id
                [last_action]
                    defined-first
                        DiscussSidebarCategory/channel
                    defined-first
                        DiscussSidebarCategory/channel
                        Thread/lastInterestDateTime
                    greater-first
                        DiscussSidebarCategory/channel
                        Thread/lastInterestDateTime
                    greater-first
                        DiscussSidebarCategory/channel
                        Thread/id
`;
