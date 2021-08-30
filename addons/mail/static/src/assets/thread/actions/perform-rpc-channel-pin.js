/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Performs the 'channel_pin' RPC on 'mail.channel'.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            Thread/performRpcChannelPin
        [Action/params]
            pinned
                [type]
                    Boolean
                [default]
                    false
            uuid
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
                        channel_pin
                    [kwargs]
                        [uuid]
                            @uuid
                        [pinned]
                            @pinned
                [1]
                    [shadow]
                        true
`;
