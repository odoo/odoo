/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            activityViewForeach
        [Element/model]
            ActivityBoxComponent
        [Record/models]
            Foreach
        [Foreach/collection]
            @record
            .{ActivityBoxComponent/activityBoxView}
            .{ActivityBoxView/activityViews}
        [Foreach/as]
            activityView
        [Element/key]
            @field
            .{Foreach/get}
                activityView
            .{Record/id}
        [Field/target]
            ActivityBoxComponent:activityView
        [ActivityBoxComponent:activityView/activityView]
            @field
            .{Foreach/get}
                activityView
`;
