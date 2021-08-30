/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Handles blur on this feedback textarea.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            ActivityMarkDonePopoverView/onBlur
        [Action/params]
            record
                [type]
                    ActivityMarkDonePopoverView
        [Action/behavior]
            {if}
                {Record/exists}
                    @record
                .{isFalsy}
                .{|}
                    @record
                    .{ActivityMarkDonePopoverView/feedbackTextareaRef}
                    .{isFalsy}
                .{|}
            .{then}
                {break}
            {ActivityMarkDonePopoverView/_backupFeedback}
                @record
`;
