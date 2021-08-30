/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            reactionContainer
        [Element/model]
            MessageViewComponent
        [web.Element/class]
            d-flex
            flex-wrap
            ml-2
`;
