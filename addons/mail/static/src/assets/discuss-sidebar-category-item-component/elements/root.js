/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            root
        [Element/model]
            DiscussSidebarCategoryItemComponent
        [Element/onClick]
            {DiscussSidebarCategoryItem/onClick}
                [0]
                    @record
                    .{DiscussSidebarCategoryItemComponent/categoryItem}
                [1]
                    @ev
        [web.Element/style]
            [web.scss/cursor]
                pointer
            [web.scss/display]
                flex
            [web.scss/align-items]
                center
            [web.scss/padding]
                [0]
                    {scss/map-get}
                        {scss/$spacers}
                        2
                [1]
                    0
            {if}
                @field
                .{Element.isHover}
            .{then}
                [web.scss/background-color]
                    {scss/gray}
                        300
            {if}
                @record
                .{DiscussSidebarCategoryItemComponent/categoryItem}
                .{DiscussSidebarCategoryItem/isActive}
            .{then}
                [web.scss/background-color]
                    {scss/gray}
                        200
`;
