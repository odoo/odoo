/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            activityList
        [Element/model]
            ActivityBoxComponent
        [Element/isPresent]
            @record
            .{ActivityBoxComponent/activityBoxView}
            .{ActivityBoxView/chatter}
            .{Chatter/thread}
            .{&}
                @record
                .{ActivityBoxComponent/activityBoxView}
                .{ActivityBoxView/isActivityListVisible}
`;
