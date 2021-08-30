/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            commandLeave
        [Element/model]
            DiscussSidebarCategoryItemComponent
        [Record/models]
            DiscussSidebarCategoryItemComponent/command
        [Element/isPresent]
            @record
            .{DiscussSidebarCategoryItemComponent/categoryItem}
            .{DiscussSidebarCategoryItem/hasLeaveCommand}
        [web.Element/class]
            fa
            fa-times
        [Element/onClick]
            {DiscussSidebarCategoryItem/onClickCommandLeave}
                @record
                .{DiscussSidebarCategoryItemComponent/categoryItem}
        [web.Element/title]
            {Locale/text}
                Leave this channel
        [web.Element/role]
            img
`;
