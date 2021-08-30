/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            callIndicator
        [Element/model]
            DiscussSidebarCategoryItemComponent
        [Element/isPresent]
            @record
            .{DiscussSidebarCategoryItemComponent/categoryItem}
            .{DiscussSidebarCategoryItem/channel}
            .{&}
                @record
                .{DiscussSidebarCategoryItemComponent/categoryItem}
                .{DiscussSidebarCategoryItem/channel}
                .{Thread/rtcSessions}
                .{Collection/length}
                .{>}
                    0
        [Record/models]
            DiscussSidebarCategoryItemComponent/item
        [web.Element/class]
            fa
            fa-volume-up
        [web.Element/style]
            [web.scss/margin-right]
                {scss/$o-mail-discuss-sidebar-scrollbar-width}
            {if}
                @record
                .{DiscussSidebarCategoryItemComponent/categoryItem}
                .{DiscussSidebarCategoryItem/channel}
                .{Thread/rtc}
            .{then}
                [web.scss/color]
                    red
`;
