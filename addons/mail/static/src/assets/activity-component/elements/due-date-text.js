/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            dueDateText
        [Element/model]
            ActivityComponent
        [web.Element/class]
            me-2
            {if}
                @record
                .{ActivityComponent/activityView}
                .{ActivityView/activity}
                .{Activity/state}
                .{=}
                    overdue
            .{then}
                text-danger
            {if}
                @record
                .{ActivityComponent/activityView}
                .{ActivityView/activity}
                .{Activity/state}
                .{=}
                    planned
            .{then}
                text-success
            {if}
                @record
                .{ActivityComponent/activityView}
                .{ActivityView/activity}
                .{Activity/state}
                .{=}
                    today
            .{then}
                text-warning
`;
