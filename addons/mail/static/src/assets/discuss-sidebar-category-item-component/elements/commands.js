/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            commands
        [Element/model]
            DiscussSidebarCategoryItemComponent
        [Record/models]
            DiscussSidebarCategoryItemComponent/item
        [Element/isPresent]
            @record
            .{DiscussSidebarCategoryItemComponent/root}
            .{web.Element/isHover}
        [web.Element/style]
            [web.scss/display]
                flex
`;
