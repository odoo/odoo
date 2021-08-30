/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Handles click on this "Done" button.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            ActivityMarkDonePopoverView/onClickDone
        [Action/params]
            record
                [type]
                    ActivityMarkDonePopoverView
        [Action/behavior]
            :chatter
                @record
                .{ActivityMarkDonePopoverView/activityViewOwner}
                .{ActivityView/activityBoxView}
            {Activity/markAsDone}
                [0]
                    @record
                    .{ActivityMarkDonePopoverView/activityViewOwner}
                    .{ActivityView/activity}
                [1]
                    [feedback]
                        @record
                        .{ActivityMarkDonePopoverView/feedbackTextareaRef}
                        .{web.Element/value}
            {if}
                {Record/exists}
                    @chatter
                .{isFalsy}
                .{|}
                    @chatter
                    .{Chatter/component}
                    .{isFalsy}
            .{then}
                {break}
            {Chatter/reloadParentView}
                @chatter
`;
