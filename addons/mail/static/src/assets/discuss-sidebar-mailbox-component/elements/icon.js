/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            icon
        [Element/model]
            DiscussSidebarMailboxComponent
        [Record/models]
            DiscussSidebarMailboxComponent/item
        [Field/target]
            ThreadIconComponent
        [ThreadIconComponent/thread]
            @record
            .{DiscussSidebarMailboxComponent/mailbox}
`;
