/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Handles click on the "refuse access" button.
    {Record/insert}
        [Record/models]
            Action
        [Action/feature]
            website_slides
        [Action/name]
            ActivityView/onRefuseAccess
        [Action/params]
            record
                [type]
                    ActivityView
            ev
                [type]
                    web.MouseEvent
        [Action/behavior]
            {Dev/comment}
                save value before deleting activity
            :chatter
                @record
                .{ActivityView/activityBoxView}
            {Env/services}
            .{Dict/get}
                rpc
            .{Function/call}
                [model]
                    slide.channel
                [method]
                    action_refuse_access
                [args]
                    @record
                    .{ActivityView/activity}
                    .{Activity/thread}
                    .{Thread/id}
                [kwargs]
                    [partner_id]
                        @record
                        .{ActivityView/activity}
                        .{Activity/requestingPartner}
                        .{Partner/id}
            {if}
                @record
                .{ActivityView/activity}
            .{then}
                {Record/delete}
                    @record
                    .{ActivityView/activity}
            {Chatter/reloadParentView}
                @chatter
`;
