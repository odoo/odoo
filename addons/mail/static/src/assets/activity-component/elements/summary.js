/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            summary
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
        [web.Element/textContent]
            @record
            .{ActivityComponent/activityView}
            .{ActivityView/summary}
`;
