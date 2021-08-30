/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            itemOpenForeach
        [Element/model]
            DiscussSidebarCategoryComponent
        [Record/models]
            Foreach
        [Foreach/collection]
            @record
            .{DiscussSidebarCategoryComponent/category}
            .{DiscussSidebarCategory/filteredCategoryItems}
        [Foreach/as]
            item
        [Element/key]
            @field
            .{Foreach/get}
                item
            .{Record/id}
        [Field/target]
            DiscussSidebarCategoryComponent:itemOpen
        [DiscussSidebarCategoryComponent:itemOpen/item]
            @field
            .{Foreach/get}
                item
`;
