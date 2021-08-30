/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determines the filtered and sorted discuss sidebar category items
        that are displayed by this discuss sidebar category.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            filteredCategoryItems
        [Field/model]
            DiscussSidebarCategory
        [Field/type]
            many
        [Field/target]
            DiscussSidebarCategoryItem
        [Field/isReadonly]
            true
        [Field/compute]
            :categoryItems
                @record
                .{DiscussSidebarCategory/categoryItems}
            :searchValue
                {Discuss/sidebarQuickSearchValue}
            {if}
                @searchValue
            .{then}
                :qsVal
                    @searchValue
                    .{String/toLowerCase}
                :categoryItems
                    @categoryItems
                    .{Collection/filter}
                        {Record/insert}
                            [Record/models]
                                Function
                            [Function/in]
                                categoryItem
                            [Function/out]
                                :nameVal
                                    @categoryItem
                                    .{DiscussSidebarCategoryItem/channel}
                                    .{Thread/displayName}
                                    .{String/toLowerCase}
                                @nameVal
                                .{String/includes}
                                    @qsVal
            @categoryItems
`;
