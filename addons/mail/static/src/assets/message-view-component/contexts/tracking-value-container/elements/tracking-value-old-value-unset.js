/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            trackingValueOldValueUnset
        [Element/model]
            MessageViewComponent:trackingValueContainer
        [Record/models]
            MessageViewComponent/trackingValueItem
        [Element/isPresent]
            @record
            .{MessageViewComponent:trackingValueContainer/value}
            .{TrackingValue/old_value}
            .{isFalsy}
        [web.Element/tag]
            i
        [web.Element/class]
            mr-2
        [web.Element/textContent]
            {Locale/text}
                None
`;
