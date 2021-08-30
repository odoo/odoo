/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            counter
        [Element/model]
            DiscussSidebarCategoryItemComponent
        [Element/isPresent]
            @record
            .{DiscussSidebarCategoryItemComponent/categoryItem}
            .{DiscussSidebarCategoryItem/counter}
            .{>}
                0
        [Record/models]
            DiscussSidebarCategoryItemComponent/item
        [web.Element/class]
            badge
            badge-pill
        [web.Element/textContent]
            @record
            .{DiscussSidebarCategoryItemComponent/categoryItem}
            .{DiscussSidebarCategoryItem/counter}
        [web.Element/style]
            [web.scss/background-color]
                {scss/$o-brand-primary}
            [web.scss/color]
                {scss/gray}
                    300
`;
