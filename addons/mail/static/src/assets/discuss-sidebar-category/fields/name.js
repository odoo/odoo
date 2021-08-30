/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Display name of the category.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            name
        [Field/model]
            DiscussSidebarCategory
        [Field/type]
            attr
        [Field/target]
            String
`;
