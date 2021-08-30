/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            descriptionCreator
        [Element/model]
            ActivityComponent
        [Element/isPresent]
            @record
            .{ActivityComponent/activityView}
            .{ActivityView/activity}
            .{Activity/creator}
        [web.Element/class]
            d-md-table-row
            mb-3
`;
