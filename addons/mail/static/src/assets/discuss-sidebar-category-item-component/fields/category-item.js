/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            categoryItem
        [Field/model]
            DiscussSidebarCategoryItemComponent
        [Field/type]
            one
        [Field/target]
            DiscussSidebarCategoryItem
        [Field/isRequired]
            true
`;
