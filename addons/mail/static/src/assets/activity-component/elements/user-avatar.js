/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            userAvatar
        [Element/model]
            ActivityComponent
        [web.Element/tag]
            img
        [web.Element/class]
            rounded-circle
            w-100
        [Element/isPresent]
            @record
            .{ActivityComponent/activityView}
            .{ActivityView/activity}
            .{Activity/assignee}
        [web.Element/src]
            /web/image/res.users/
            .{+}
                @record
                .{ActivityComponent/activityView}
                .{ActivityView/activity}
                .{Activity/assignee}
                .{User/id}
            .{+}
                /avatar_128
        [web.Element/alt]
            @record
            .{ActivityComponent/activityView}
            .{ActivityView/activity}
            .{Activity/assignee}
            .{User/nameOrDisplayName}
`;
