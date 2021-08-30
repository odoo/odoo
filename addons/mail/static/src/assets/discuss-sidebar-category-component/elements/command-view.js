/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            commandView
        [Element/model]
            DiscussSidebarCategoryComponent
        [Record/models]
            DiscussSidebarCategoryComponent/command
        [Element/isPresent]
            @record
            .{DiscussSidebarCategoryComponent/category}
            .{DiscussSidebarCategory/hasViewCommand}
        [web.Element/tag]
            i
        [web.Element/class]
            fa
            fa-cog
        [web.Element/title]
            {Locale/text}
                View or join channels
        [Element/onClick]
            {DiscussSidebarCategory/onClickCommandView}
                [0]
                    @record
                    .{DiscussSidebarCategoryComponent/category}
                [1]
                    @ev
        [web.Element/role]
            img
`;
