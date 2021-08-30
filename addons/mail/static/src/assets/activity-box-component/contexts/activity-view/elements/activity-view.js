/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            activityView
        [Element/model]
            ActivityBoxComponent:activityView
        [Field/target]
            ActivityComponent
        [ActivityComponent/activityView]
            @record
            .{ActivityBoxComponent:activityView/activityView}
`;
