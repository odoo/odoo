/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            root
        [Element/model]
            DiscussPublicViewComponent
        [web.Element/class]
            d-flex
            flex-column
            h-100
`;
