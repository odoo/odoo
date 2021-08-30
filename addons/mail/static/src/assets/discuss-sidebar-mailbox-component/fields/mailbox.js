/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            mailbox
        [Field/model]
            DiscussSidebarMailboxComponent
        [Field/type]
            one
        [Field/target]
            Thread
`;
