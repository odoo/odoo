/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            counter
        [Element/model]
            DiscussSidebarCategoryComponent
        [Record/models]
            DiscussSidebarCategoryComponent/headerItem
        [Element/isPresent]
            @record
            .{DiscussSidebarCategoryComponent/category}
            .{DiscussSidebarCategory/isOpen}
            .{isFalsy}
            .{&}
                @record
                .{DiscussSidebarCategoryComponent/category}
                .{DiscussSidebarCategory/counter}
                .{>}
                    0
        [web.Element/class]
            badge
            badge-pill
        [web.Element/textContent]
            @record
            .{DiscussSidebarCategoryComponent/category}
            .{DiscussSidebarCategory/counter}
        [web.Element/style]
            [web.scss/background-color]
                {scss/$o-brand-primary}
            [web.scss/color]
                {scss/gray}
                    300
`;
