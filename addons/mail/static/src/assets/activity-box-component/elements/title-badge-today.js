/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            titleBadgeToday
        [Element/model]
            ActivityBoxComponent
        [Record/models]
            ActivityBoxComponent/titleBadge
        [web.Element/class]
            badge-warning
        [Element/isPresent]
            @record
            .{ActivityBoxComponent/activityBoxView}
            .{ActivityBoxView/chatter}
            .{Chatter/thread}
            .{Thread/todayActivities}
            .{Collection/length}
            .{>}
                0
        [web.Element/textContent]
            @record
            .{ActivityBoxComponent/activityBoxView}
            .{ActivityBoxView/chatter}
            .{Chatter/thread}
            .{Thread/todayActivities}
            .{Collection/length}
`;
