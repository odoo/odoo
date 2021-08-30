/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        States the total amount of unread/action-needed threads in this
        category.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            counter
        [Field/model]
            DiscussSidebarCategory
        [Field/type]
            attr
        [Field/target]
            Integer
        [Field/default]
            0
        [Field/isReadonly]
            true
        [Field/sum]
            DiscussSidebarCategory/categoryItems
            DiscussSidebarCategoryItem/categoryCounterContribution
`;
