/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        The key used in the server side for the category state
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            serverStateKey
        [Field/model]
            DiscussSidebarCategory
        [Field/type]
            attr
        [Field/isReadonly]
            true
        [Field/isRequired]
            true
`;
