/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            addingItem
        [Element/model]
            DiscussSidebarCategoryComponent
        [Element/isPresent]
            @record
            .{DiscussSidebarCategoryComponent/category}
            .{DiscussSidebarCategory/isOpen}
            .{&}
                @record
                .{DiscussSidebarCategoryComponent/category}
                .{DiscussSidebarCategory/isAddingItem}
        [web.Element/class]
            d-flex
            mb-2
`;
