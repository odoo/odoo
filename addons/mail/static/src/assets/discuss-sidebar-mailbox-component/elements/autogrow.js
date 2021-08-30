/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            autogrow
        [Element/model]
            DiscussSidebarMailboxComponent
        [Record/models]
            AutogrowComponent
            DiscussSidebarMailboxComponent/item
`;
