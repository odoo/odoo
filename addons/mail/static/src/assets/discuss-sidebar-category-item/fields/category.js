/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determines the discuss sidebar category displaying this.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            category
        [Field/model]
            DiscussSidebarCategoryItem
        [Field/type]
            one
        [Field/target]
            DiscussSidebarCategory
        [Field/isReadonly]
            true
        [Field/isRequired]
            true
        [Field/inverse]
            DiscussSidebarCategory/categoryItems
`;
