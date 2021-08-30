/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            separator
        [Element/model]
            DiscussSidebarComponent
        [web.Element/tag]
            hr
        [web.Element/style]
            [web.scss/width]
                100%
            [web.scss/background-color]
                {scss/$border-color}
`;
