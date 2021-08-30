/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Performs the '/mail/channel/set_last_seen_message' RPC.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            Thread/performRpcChannelSeen
        [Action/params]
            id
                [type]
                    Integer
                [description]
                    id of channel
            lastMessageId
                [type]
                    Integer
        [Action/behavior]
            @env
            .{Env/owlEnv}
            .{Dict/get}
                services
            .{Dict/get}
                rpc
            .{Function/call}
                [0]
                    [route]
                        /mail/channel/set_last_seen_message
                    [params]
                        [channel_id]
                            @id
                        [last_message_id]
                            @lastMessageId
                [1]
                    [shadow]
                        true
`;
