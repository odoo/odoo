/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            itemOpen
        [Element/model]
            DiscussSidebarCategoryComponent:itemOpen
        [Record/models]
            DiscussSidebarCategoryComponent/item
        [Field/target]
            DiscussSidebarCategoryItemComponent
        [DiscussSidebarCategoryItemComponent/categoryItem]
            @record
            .{DiscussSidebarCategoryComponent:itemOpen/item}
`;
