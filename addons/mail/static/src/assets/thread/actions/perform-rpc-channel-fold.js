/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Performs the 'channel_fold' RPC on 'mail.channel'.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            Thread/performRpcChannelFold
        [Action/params]
            uuid
                [type]
                    String
            state
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
                [0]
                    [model]
                        mail.channel
                    [method]
                        channel_fold
                    [kwargs]
                        [state]
                            @state
                        [uuid]
                            @uuid
                [1]
                    [shadow]
                        true
`;
