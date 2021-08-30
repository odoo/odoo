/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            Activity/markAsDone
        [Action/params]
            record
        [Action/behavior]
            :attachmentIds
                @attachments
                .{Collection/map}
                    {Record/insert}
                        [Record/models]
                            Function
                        [Function/in]
                            attachment
                        [Function/out]
                            @attachment
                            .{Attachment/id}
            {Record/doAsync}
                [0]
                    @record
                [1]
                    {Env/owlEnv}
                    .{Dict/get}
                        services
                    .{Dict/get}
                        rpc
                    .{Function/call}
                        [model]
                            mail.activity
                        [method]
                            action_feedback
                        [args]
                            @record
                            .{Activity/id}
                        [kwargs]
                            [attachment_ids]
                                @attachmentIds
                            [feedback]
                                @feedback
            {Thread/fetchData}
                [0]
                    @record
                    .{Activity/thread}
                [1]
                    attachments
                    messages
            {Record/delete}
                @record
`;
