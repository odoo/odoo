/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            root
        [Element/model]
            DiscussContainerComponent
        [web.Element/class]
            d-flex
            flex-grow-1
            flex-column
`;
