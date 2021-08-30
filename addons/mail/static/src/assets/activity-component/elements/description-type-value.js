/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            descriptionTypeValue
        [Element/model]
            ActivityComponent
        [web.Element/class]
            d-md-table-cell
            py-md-1
            pr-4
        [web.Element/textContent]
            @record
            .{ActivityComponent/activityView}
            .{ActivityView/activity}
            .{Activity/type}
            .{ActivityType/displayName}
`;
