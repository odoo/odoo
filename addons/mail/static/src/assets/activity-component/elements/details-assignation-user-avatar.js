/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            detailsAssignationUserAvatar
        [Element/model]
            ActivityComponent
        [web.Element/tag]
            img
        [Record/models]
            ActivityComponent/detailsUserAvatar
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
        [web.Element/title]
            @record
            .{ActivityComponent/activityView}
            .{ActivityView/activity}
            .{Activity/assignee}
            .{User/nameOrDisplayName}
        [web.Element/alt]
            @record
            .{ActivityComponent/activityView}
            .{ActivityView/activity}
            .{Activity/assignee}
            .{User/nameOrDisplayName}
`;
