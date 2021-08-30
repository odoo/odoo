/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            titleIcon
        [Element/model]
            DiscussSidebarCategoryComponent
        [web.Element/tag]
            i
        [web.Element/class]
            fa
            {if}
                @record
                .{DiscussSidebarCategoryComponent/category}
                .{DiscussSidebarCategory/isOpen}
            .{then}
                fa-chevron-down
            .{else}
                fa-chevron-right
        [web.Element/style]
            [web.scss/width]
                {scss/$o-mail-discuss-sidebar-category-title-icon-size}
            [web.scss/height]
                {scss/$o-mail-discuss-sidebar-category-title-icon-size}
            [font-size]
                0.75
                em
`;
