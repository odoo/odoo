/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            discussView
        [Field/model]
            DiscussSidebarComponent
        [Field/type]
            one
        [Field/target]
            DiscussView
        [Field/isRequired]
            true
`;
