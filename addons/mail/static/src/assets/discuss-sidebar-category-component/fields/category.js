/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            category
        [Field/model]
            DiscussSidebarCategoryComponent
        [Field/type]
            one
        [Field/target]
            DiscussSidebarCategory
        [Field/isRequired]
            true
`;
