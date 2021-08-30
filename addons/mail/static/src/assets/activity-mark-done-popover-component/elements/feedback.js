/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            feedback
        [Element/model]
            ActivityMarkDonePopoverComponent
        [web.Element/tag]
            textarea
        [web.Element/class]
            form-control
            mb-2
        [web.Element/rows]
            3
        [web.Element/placeholder]
            {Locale/text}
                Write Feedback
        [web.Element/placeholder]
            {Locale/text}
                Write Feedback
        [Element/onBlur]
            {ActivityMarkDonePopoverView/onBlur}
                [0]
                    @record
                    .{ActivityMarkDonePopoverComponent/activityMarkDonePopoverView}
                [1]
                    @ev
        [web.Element/style]
            [web.scss/min-height]
                70
                px
`;
