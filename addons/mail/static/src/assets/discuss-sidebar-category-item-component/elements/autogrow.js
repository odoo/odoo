/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            autogrow
        [Element/model]
            DiscussSidebarCategoryItemComponent
        [Record/models]
            AutogrowComponent
            DiscussSidebarCategoryItemComponent/item
`;
