/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            MailTemplate/send
        [Action/params]
            activity
                [type]
                    Activity
            mailTemplate
                [type]
                    MailTemplate
        [Action/behavior]
            {Record/doAsync}
                [0]
                    @mailTemplate
                [1]
                    @env
                    .{Env/owlEnv}
                    .{Dict/get}
                        services
                    .{Dict/get}
                        rpc
                    .{Function/call}
                        [model]
                            @activity
                            .{Activity/thread}
                            .{Thread/model}
                        [method]
                            activity_send_mail
                        [args]
                            {Record/insert}
                                [Record/models]
                                    Collection
                                [0]
                                    @activity
                                    .{Activity/thread}
                                    .{Thread/id}
                                [1]
                                    @mailTemplate
                                    .{MailTemplate/id}
            {Thread/fetchData}
                [0]
                    @activity
                    .{Activity/thread}
                [1]
                    attachments
                    messages
`;
