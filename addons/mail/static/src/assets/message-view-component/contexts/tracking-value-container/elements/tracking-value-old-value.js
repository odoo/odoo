/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            trackingValueOldValue
        [Element/model]
            MessageViewComponent:trackingValueContainer
        [Record/models]
            MessageViewComponent/trackingValueItem
        [Element/isPresent]
            @record
            .{MessageViewComponent:trackingValueContainer/value}
            .{TrackingValue/old_value}
        [web.Element/textContent]
            @record
            .{MessageViewComponent:trackingValueContainer/value}
            .{TrackingValue/old_value}
`;
