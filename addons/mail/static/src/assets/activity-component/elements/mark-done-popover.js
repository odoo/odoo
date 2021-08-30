/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            markDonePopover
        [Element/model]
            ActivityComponent
        [Field/target]
            PopoverComponent
        [PopoverComponent/position]
            right
        [PopoverComponent/title]
            @record
            .{ActivityComponent/activityView}
            .{ActivityView/markDoneText}
        [PopoverComponent/content]
            {Record/insert}
                [Record/models]
                    ActivityMarkDonePopoverComponent
                [ActivityMarkDonePopoverComponent/activityMarkDonePopoverView]
                    @record
                    .{ActivityComponent/activityView}
                    .{ActivityView/activityMarkDonePopoverView}
`;
