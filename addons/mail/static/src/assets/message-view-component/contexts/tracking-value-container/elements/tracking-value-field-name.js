/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            trackingValueFieldName
        [Element/model]
            MessageViewComponent:trackingValueContainer
        [Record/models]
            MessageViewComponent/trackingValueItem
        [web.Element/textContent]
            @record
            .{MessageViewComponent:trackingValueContainer/value}
            .{TrackingValue/changed_field}
`;
