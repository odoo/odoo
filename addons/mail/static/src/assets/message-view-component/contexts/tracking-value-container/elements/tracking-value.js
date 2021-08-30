/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            trackingValue
        [Element/model]
            MessageViewComponent:trackingValueContainer
        [web.Element/style]
            [web.scss/display]
                flex
            [web.scss/align-items]
                center
            [web.scss/flex-wrap]
                wrap
`;
