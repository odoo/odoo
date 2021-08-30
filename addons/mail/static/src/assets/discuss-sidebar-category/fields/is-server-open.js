/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Boolean that determines the last open state known by the server.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            isServerOpen
        [Field/model]
            DiscussSidebarCategory
        [Field/type]
            attr
        [Field/target]
            Boolean
`;
