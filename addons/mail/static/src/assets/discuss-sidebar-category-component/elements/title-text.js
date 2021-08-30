/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            titleText
        [Element/model]
            DiscussSidebarCategoryComponent
        [web.Element/tag]
            spam
        [web.Element/textContent]
            @record
            .{DiscussSidebarCategoryComponent/category}
            .{DiscussSidebarCategory/name}
        [web.Element/style]
            [web.scss/font-size]
                {scss/$font-size-sm}
            [web.scss/text-transform]
                uppercase
            [web.scss/font-weight]
                bolder
`;
