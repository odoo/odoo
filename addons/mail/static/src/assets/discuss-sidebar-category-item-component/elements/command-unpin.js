/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            commandUnpin
        [Element/model]
            DiscussSidebarCategoryItemComponent
        [Record/models]
            DiscussSidebarCategoryItemComponent/command
        [Element/isPresent]
            @record
            .{DiscussSidebarCategoryItemComponent/categoryItem}
            .{DiscussSidebarCategoryItem/hasUnpinCommand}
        [web.Element/class]
            fa
            fa-times
        [Element/onClick]
            {DiscussSidebarCategoryItem/onClickCommandUnpin}
                @record
                .{DiscussSidebarCategoryItemComponent/categoryItem}
        [web.Element/title]
            {Locale/text}
                Unpin Conversation
        [web.Element/role]
            img
`;
