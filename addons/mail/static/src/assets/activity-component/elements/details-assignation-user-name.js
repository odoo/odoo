/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            detailsAssignationUserName
        [Element/model]
            ActivityComponent
        [web.Element/tag]
            b
        [web.Element/textContent]
            @record
            .{ActivityComponent/activityView}
            .{ActivityView/activity}
            .{Activity/assignee}
            .{User/nameOrDisplayName}
`;
