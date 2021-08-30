/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            avatar
        [Element/model]
            DiscussSidebarCategoryItemComponent
        [Record/models]
            DiscussSidebarCategoryItemComponent/item
`;
