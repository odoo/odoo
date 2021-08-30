/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            trackingValueSeparator
        [Element/model]
            MessageViewComponent:trackingValueContainer
        [Record/models]
            MessageViewComponent/trackingValueItem
        [web.Element/class]
            fa
            fa-long-arrow-right
        [web.Element/title]
            {Locale/text}
                Changed
        [web.Element/role]
            img
`;
