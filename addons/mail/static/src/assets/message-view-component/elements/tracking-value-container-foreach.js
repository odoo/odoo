/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            trackingValueContainerForeach
        [Element/model]
            MessageViewComponent
        [Record/models]
            Foreach
        [Field/target]
            MessageViewComponent:trackingValueContainer
        [Foreach/collection]
            {MessageViewComponent/getTrackingValues}
                @record
        [MessageViewComponent:trackingValueContainer/value]
            @field
            .{Foreach/get}
                value
        [Foreach/as]
            value
        [Element/key]
            @field
            .{Foreach/get}
                value
            .{TrackingValue/id}
`;
