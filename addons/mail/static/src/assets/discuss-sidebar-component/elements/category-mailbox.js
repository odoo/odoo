/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            categoryMailbox
        [Element/model]
            DiscussSidebarComponent
        [Record/models]
            DiscussSidebarComponent/category
`;
