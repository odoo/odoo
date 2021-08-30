/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determines how the autocomplete of this category should behave.
        Must be one of: 'channel', 'chat'.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            autocompleteMethod
        [Field/model]
            DiscussSidebarCategory
        [Field/type]
            attr
`;
