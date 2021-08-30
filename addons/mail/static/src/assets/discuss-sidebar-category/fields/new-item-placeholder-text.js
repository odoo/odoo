/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        The placeholder text used when a new item is being added in UI.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            newItemPlaceholderText
        [Field/model]
            DiscussSidebarCategory
        [Field/type]
            attr
        [Field/target]
            String
`;
