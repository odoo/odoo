/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            trackingValueContainer
        [Element/model]
            MessageViewComponent:trackingValueContainer
        [web.Element/tag]
            li
`;
