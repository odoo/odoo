/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            activityBox
        [Element/model]
            ChatterComponent
        [Field/target]
            ActivityBoxComponent
        [Element/isPresent]
            @record
            .{ChatterComponent/chatter}
            .{Chatter/activityBoxView}
        [ActivityBoxComponent/activityBoxView]
            @record
            .{ChatterComponent/chatter}
            .{Chatter/activityBoxView}
`;
