/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Handles keydown on this activity mark done.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            ActivityMarkDonePopoverView/onKeydown
        [Action/params]
            ev
                [type]
                    web.KeyboardEvent
            record
                [type]
                    ActivityMarkDonePopoverView
        [Action/behavior]
            {if}
                @ev
                .{web.KeyboardEvent/key}
                .{=}
                    Escape
            .{then}
                {ActivityMarkDonePopoverView/_close}
                    @record
`;
