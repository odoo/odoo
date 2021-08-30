/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            doneButton
        [Element/model]
            ActivityMarkDonePopoverComponent
        [web.Element/tag]
            button
        [web.Element/class]
            btn
            btn-sm
            btn-primary
            mx-2
        [web.Element/type]
            button
        [Element/isPresent]
            @record
            .{ActivityMarkDonePopoverComponent/activityMarkDonePopoverView}
            .{ActivityMarkDonePopoverView/activity}
            .{Activity/chainingType}
            .{=}
                suggest
        [Element/onClick]
            {ActivityMarkDonePopoverView/onClickDone}
                [0]
                    @record
                    .{ActivityMarkDonePopoverComponent/activityMarkDonePopoverView}
                [1]
                    @ev
        [web.Element/textContent]
            {Locale/text}
                Done
`;
