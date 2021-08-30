/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            category
        [Element/model]
            DiscussSidebarComponent
        [Model/style]
            [web.scss/display]
                flex
            [web.scss/flex-flow]
                column
            [web.scss/flex]
                0
                0
                auto
`;
