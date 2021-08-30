/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            ActivityMarkDonePopoverView/_backupFeedback
        [Action/params]
            record
                [type]
                    ActivityMarkDonePopoverView
        [Action/behavior]
            {Record/update}
                [0]
                    @record
                    .{ActivityMarkDonePopoverView/activityViewOwner}
                    .{ActivityView/activity}
                [1]
                    [Activity/feedbackBackup]
                        @record
                        .{ActivityMarkDonePopoverView/feedbackTextareaRef}
                        .{web.Element/value}
`;
