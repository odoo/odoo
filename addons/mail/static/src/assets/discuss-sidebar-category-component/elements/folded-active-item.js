/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            foldedActiveItem
        [Element/model]
            DiscussSidebarCategoryComponent
        [Record/models]
            DiscussSidebarCategoryComponent/item
        [Element/isPresent]
            @record
            .{DiscussSidebarCategoryComponent/category}
            .{DiscussSidebarCategory/isOpen}
            .{isFalsy}
            .{&}
                @record
                .{DiscussSidebarCategoryComponent/category}
                .{DiscussSidebarCategory/activeItem}
        [Field/target]
            DiscussSidebarCategoryItemComponent
        [DiscussSidebarCategoryItemComponent/categoryItem]
            @record
            .{DiscussSidebarCategoryComponent/category}
            .{DiscussSidebarCategory/activeItem}
`;
