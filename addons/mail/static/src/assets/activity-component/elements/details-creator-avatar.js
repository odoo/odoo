/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            detailsCreatorAvatar
        [Element/model]
            ActivityComponent
        [web.Element/tag]
            img
        [web.Element/class]
            ms-1
            me-1
            rounded-circle
            align-text-bottom
        [Record/models]
            ActivityComponent/detailsUserAvatar
        [web.Element/src]
            /web/image/res.users/
            .{+}
                @record
                .{ActivityComponent/activityView}
                .{ActivityView/activity}
                .{Activity/creator}
                .{User/id}
            .{+}
                /avatar_128
        [web.Element/title]
            @record
            .{ActivityComponent/activityView}
            .{ActivityView/activity}
            .{Activity/creator}
            .{User/nameOrDisplayName}
        [web.Element/alt]
            @record
            .{ActivityComponent/activityView}
            .{ActivityView/activity}
            .{Activity/creator}
            .{User/nameOrDisplayName}
`;
