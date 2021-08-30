/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Test
        [Test/name]
            receive new chat message: out of odoo focus
        [Test/model]
            DiscussComponent
        [Test/assertions]
            4
        [Test/scenario]
            {Dev/comment}
                channel expected to be found in the sidebar
                with a random unique id that will be referenced in the test
            :bus
                {Record/insert}
                    [Record/models]
                        Bus
            {Bus/on}
                [0]
                    @bus
                [1]
                    set_title_part
                [2]
                    null
                [3]
                    {Record/insert}
                        [Record/models]
                            Function
                        [Function/in]
                            payload
                        [Function/out]
                            {Test/step}
                                set_title_part
                            {Test/assert}
                                @payload
                                .{Dict/get}
                                    part
                                .{=}
                                    _chat
                            {Test/assert}
                                @payload
                                .{Dict/get}
                                    title
                                .{=}
                                    1 Message
            :testEnv
                {Record/insert}
                    [Record/models]
                        Env
                    [Env/owlEnv]
                        [bus]
                            @bus
                        [services]
                            [bus_service]
                                {Record/insert}
                                    [Record/models]
                                        BusService
                                    [_beep]
                                        {Dev/comment}
                                            Do nothing
                                    [_poll]
                                        {Dev/comment}
                                            Do nothing
                                    [_registerWindowUnload]
                                        {Dev/comment}
                                            Do nothing
                                    [isOdooFocused]
                                        false
                                    [updateOption]
            @testEnv
            .{Record/insert}
                [Record/models]
                    mail.channel
                [mail.channel/channel_type]
                    chat
                [mail.channel/id]
                    20
            @testEnv
            .{Record/insert}
                [Record/models]
                    Server
                [Server/data]
                    @record
                    .{Test/data}
            @testEnv
            .{Record/insert}
                [Record/models]
                    DiscussComponent
            {Dev/comment}
                simulate receiving a new message with odoo focused
            @testEnv
            .{Component/afterNextRender}
                @testEnv
                .{Env/owlEnv}
                .{Dict/get}
                    services
                .{Dict/get}
                    bus_service
                .{Dict/get}
                    trigger
                .{Function/call}
                    [0]
                        notification
                    [1]
                        [type]
                            mail.channel/new_message
                        [payload]
                            [id]
                                10
                            [message]
                                [id]
                                    126
                                [model]
                                    mail.channel
                                [res_id]
                                    10
            {Test/verifySteps}
                set_title_part
`;
