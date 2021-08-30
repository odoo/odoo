/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Executes this command on the given 'mail.channel'.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            ChannelCommand/execute
        [Action/params]
            channel
                [type]
                    Thread
            body
                [type]
                    String
        [Action/behavior]
            @env
            .{Env/owlEnv}
            .{Dict/get}
                services
            .{Dict/get}
                rpc
            .{Function/call}
                [model]
                    mail.channel
                [method]
                    @record
                    .{ChannelCommand/methodName}
                [args]
                    {Record/insert}
                        [Record/models]
                            Collection
                        {Record/insert}
                            [Record/models]
                                Collection
                            @channel
                            .{Thread/id}
                [kwargs]
                    [body]
                        @body
`;
