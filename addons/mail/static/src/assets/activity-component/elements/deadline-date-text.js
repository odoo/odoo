/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            deadlineDateText
        [Element/model]
            ActivityComponent
        [web.Element/tag]
            span
        [web.Element/textContent]
            @record
            .{ActivityComponent/activityView}
            .{ActivityView/formattedDeadlineDate}
        [web.Element/class]
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
