/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            item
        [Element/model]
            DiscussSidebarCategoryItemComponent
        [Record/models]
            DiscussSidebarCategoryItemComponent/item
        [web.Element/style]
            [web.scss/margin-left]
                {scss/$o-mail-discuss-sidebar-category-item-margin}
            [web.scss/margin-right]
                {scss/$o-mail-discuss-sidebar-category-item-margin}
            {if}
                @field
                .{web.Element/isFirst}
            .{then}
                [web.scss/margin-left]
                    {scss/$o-mail-discuss-sidebar-category-item-avatar-left-margin}
            {if}
                @field
                .{web.Element/isLast}
            .{then}
                [scss/margin-right]
                    {scss/$o-mail-discuss-sidebar-scrollbar-width}
`;
