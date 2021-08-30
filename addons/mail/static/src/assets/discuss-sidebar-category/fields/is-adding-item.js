/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Boolean that determines whether discuss is adding a new category item.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            isAddingItem
        [Field/model]
            DiscussSidebarCategory
        [Field/type]
            attr
        [Field/target]
            Boolean
        [Field/default]
            false
`;
