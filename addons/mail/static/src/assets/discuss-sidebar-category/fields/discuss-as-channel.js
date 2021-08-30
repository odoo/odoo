/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            discussAsChannel
        [Field/model]
            DiscussSidebarCategory
        [Field/type]
            one
        [Field/target]
            Discuss
        [Field/isReadonly]
            true
        [Field/inverse]
            Discuss/categoryChannel
`;
