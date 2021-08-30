/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            command
        [Element/model]
            DiscussSidebarCategoryItemComponent
        [Record/models]
            Hoverable
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
                    0
                    px
            {if}
                @field
                .{web.Element/isLast}
            .{then}
                [web.scss/margin-right]
                    0
                    px
            {if}
                @field
                .{web.Element/isHover}
                .{isFalsy}
            .{then}
                [web.scss/color]
                    {scss/gray}
                        600
`;
