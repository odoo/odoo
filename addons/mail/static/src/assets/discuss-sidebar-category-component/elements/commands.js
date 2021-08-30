/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            commands
        [Element/model]
            DiscussSidebarCategoryComponent
        [Record/models]
            DiscussSidebarCategoryComponent/headerItem
        [web.Element/style]
            [web.scss/display]
                flex
`;
