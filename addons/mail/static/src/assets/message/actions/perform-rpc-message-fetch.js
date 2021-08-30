/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Performs the 'message_fetch' RPC on 'mail.message'.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            Message/performRpcMessageFetch
        [Action/params]
            route
                [type]
                    String
            params
                [type]
                    Object
        [Action/result]
            Collection<Message>
        [Action/behavior]
            messagesData:
                @env
                .{Env/owlEnv}
                .{Dict/get}
                    services
                .{Dict/get}
                    rpc
                .{Function/call}
                    [0]
                        [route]
                            @route
                        [params]
                            @params
                    [1]
                        [shadow]
                            true
            :messages
                {Record/insert}
                    [Record/models]
                        Message
                    @messagesData
                    .{Collection/map}
                        {Record/insert}
                            [Record/models]
                                Function
                            [Function/in]
                                item
                            [Function/out]
                                {Message/convertData}
                                    @item
            {Dev/comment}
                compute seen indicators (if applicable)
            {foreach}
                @messages
            .{as}
                message
            .{do}
                {foreach}
                    @message
                    .{Message/threads}
                .{as}
                    thread
                .{do}
                    const thread of
                    {if}
                        @thread
                        .{Thread/model}
                        .{!=}
                            mail.channel
                        .{|}
                            @thread
                            .{Thread/channelType}
                            .{=}
                                channel
                    .{then}
                        {Dev/comment}
                            disabled on non-channel threads and
                            on 'channel' channels for performance reasons
                        {continue}
                    {Record/insert}
                        [Record/models]
                            MessageSeenIndicator
                        [MessageSeenIndicator/thread]
                            @thread
                        [MessageSeenIndicator/message]
                            @message
            @messages
`;
