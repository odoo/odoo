/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            name
        [Element/model]
            DiscussSidebarMailboxComponent
        [Record/models]
            DiscussSidebarMailboxComponent/item
        [web.Element/textContent]
            @record
            .{DiscussSidebarMailboxComponent/mailbox}
            .{Thread/displayName}
        [web.Element/style]
            {web.scss/include}
                {web.scss/text-truncate}
`;
