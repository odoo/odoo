/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            bottomPart
        [Element/model]
            ThreadViewComponent
        [web.Element/class]
            d-flex
            flex-grow-1
        [web.Element/style]
            [web.scss/min-height]
                0
`;
