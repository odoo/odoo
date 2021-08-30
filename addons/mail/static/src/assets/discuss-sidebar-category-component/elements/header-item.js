/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            headerItem
        [Element/model]
            DiscussSidebarCategoryComponent
        [web.Element/style]
            [web.scss/margin-left]
                {scss/$o-mail-discuss-sidebar-category-item-margin}
            [web.scss/margin-right]
                {scss/$o-mail-discuss-sidebar-category-item-margin}
            {if}
                @field
                .{web.Element/isLast}
            .{then}
                [web.scss/margin-right]
                    {scss/$o-mail-discuss-sidebar-scrollbar-width}
            [web.scss/user-select]
                none
`;
