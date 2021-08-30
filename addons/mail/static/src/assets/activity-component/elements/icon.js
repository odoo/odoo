/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            icon
        [Element/model]
            ActivityComponent
        [web.Element/tag]
            i
        [web.Element/class]
            fa
            small
            @record
            .{ActivityComponent/activityView}
            .{ActivityView/activity}
            .{Activity/icon}
`;
