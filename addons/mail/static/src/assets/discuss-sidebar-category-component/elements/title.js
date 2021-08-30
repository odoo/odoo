/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            title
        [Element/model]
            DiscussSidebarCategoryComponent
        [Record/models]
            DiscussSidebarCategoryComponent/headerItem
            Hoverable
        [Element/onClick]
            {DiscussSidebarCategory/onClick}
                @record
                .{DiscussSidebarCategoryComponent/category}
        [web.Element/style]
            [web.scss/display]
                flex
            [web.scss/align-items]
                baseline
            [web.scss/cursor]
                pointer
            {if}
                @field
                .{web.Element/isHover}
                .{isFalsy}
            .{then}
                [web.scss/color]
                    {scss/gray}
                        600
`;
