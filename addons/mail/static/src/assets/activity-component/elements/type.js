/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            type
        [Element/model]
            ActivityComponent
        [web.Element/tag]
            b
        [web.Element/class]
            text-900
            me-2
        [Element/isPresent]
            @record
            .{ActivityComponent/activityView}
            .{ActivityView/activity}
            .{Activity/summary}
            .{isFalsy}
            .{&}
                @record
                .{ActivityComponent/activityView}
                .{ActivityView/activity}
                .{Activity/type}
        [web.Element/textContent]
            @record
            .{ActivityComponent/activityView}
            .{ActivityView/activity}
            .{Activity/type}
            .{ActivityType/displayName}
        [web.Element/style]
            [web.scss/margin-inline-end]
                {scss/map-get}
                    {scss/$spacers}
                    2
            [web.scss/font-weight]
                bolder
            [web.scss/color]
                {scss/gray}
                    900
`;
