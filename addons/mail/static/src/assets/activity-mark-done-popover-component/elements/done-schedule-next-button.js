/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            doneScheduleNextButton
        [Element/model]
            ActivityMarkDonePopoverComponent
        [web.Element/tag]
            button
        [web.Element/class]
            btn
            btn-sm
            btn-primary
        [web.Element/type]
            button
        [Element/onClick]
            {ActivityMarkDonePopoverView/onClickDoneAndScheduleNext}
                [0]
                    @record
                    .{ActivityMarkDonePopoverComponent/activityMarkDonePopoverView}
                [1]
                    @ev
        [web.Element/textContent]
            {Locale/text}
                Done & Schedule Next
`;
