/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            commandAdd
        [Element/model]
            DiscussSidebarCategoryComponent
        [Record/models]
            DiscussSidebarCategoryComponent/command
        [Element/isPresent]
            @record
            .{DiscussSidebarCategoryComponent/category}
            .{DiscussSidebarCategory/hasAddCommand}
            .{&}
                @record
                .{DiscussSidebarCategoryComponent/category}
                .{DiscussSidebarCategory/isOpen}
        [web.Element/tag]
            i
        [web.Element/class]
            fa
            fa-plus
        [web.Element/title]
            @record
            .{DiscussSidebarCategoryComponent/category}
            .{DiscussSidebarCategory/commandAddTitleText}
        [Element/onClick]
            {DiscussSidebarCategory/onClickCommandAdd}
                [0]
                    @record
                    .{DiscussSidebarCategoryComponent/category}
                [1]
                    @ev
        [web.Element/role]
            img
`;
