/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            ActivityMarkDonePopoverView/_close
        [Action/params]
            record
                [type]
                    ActivityMarkDonePopoverView
        [Action/behavior]
            {ActivityMarkDonePopoverView/_backupFeedback}
                @record
            {Component/trigger}
                [0]
                    @record
                    .{ActivityMarkDonePopoverView/component}
                [1]
                    o-popover-close
`;
