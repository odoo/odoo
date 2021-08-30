/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            nonEditableName
        [Element/model]
            DiscussSidebarCategoryItemComponent
        [Record/models]
            DiscussSidebarCategoryItemComponent/item
            DiscussSidebarCategoryItemComponent/name
        [web.Element/tag]
            span
        [web.Element/class]
            ml-3
            text-truncate
        [web.Element/style]
            {if}
                @record
                .{DiscussSidebarCategoryItemComponent/categoryItem}
                .{DiscussSidebarCategoryItem/isUnread}
            {then}
                [web.scss/font-weight]
                    bold
        [web.Element/textContent]
            @record
            .{DiscussSidebarCategoryItemComponent/categoryItem}
            .{DiscussSidebarCategoryItem/channel}
            .{Thread/displayName}
`;
