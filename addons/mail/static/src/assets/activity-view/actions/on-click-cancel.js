/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Handles the click on the cancel button
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            ActivityView/onClickCancel
        [Action/params]
            record
                [type]
                    ActivityView
        [Action/behavior]
            {Dev/comment}
                save value before deleting activity
            :chatter
                @record
                .{ActivityView/activityBoxView}
                .{ActivityBoxView/chatter}
            {Activity/deleteServerRecord}
                @record
                .{ActivityView/activity}
            {Chatter/reloadParentView}
                @chatter
`;
