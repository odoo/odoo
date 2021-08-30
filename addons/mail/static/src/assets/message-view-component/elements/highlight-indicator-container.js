/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            highlightIndicatorContainer
        [Element/model]
            MessageViewComponent
        [web.Element/class]
            f-flex
            flex-shrink-0
`;
