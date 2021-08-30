/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Boolean that determines whether this category has a 'add' command.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            hasAddCommand
        [Field/model]
            DiscussSidebarCategory
        [Field/type]
            attr
        [Field/target]
            Boolean
        [Field/default]
            false
`;
