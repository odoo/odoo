/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Test
        [Test/name]
            openChat: display notification for partner without user
        [Test/model]
            Env
        [Test/assertions]
            2
        [Test/scenario]
            :testEnv
                {Record/insert}
                    [Record/models]
                        Env
                    [Env/owlEnv]
                        [services]
                            [notification]
                                [notify]
                                    {Record/insert}
                                        [Record/models]
                                            Function
                                        [Function/in]
                                            notification
                                        [Function/out]
                                            {Test/assert}
                                                [0]
                                                    @record
                                                [1]
                                                    true
                                                [1]
                                                    should display a toast notification after failing to open chat
                                            {Test/assert}
                                                [0]
                                                    @record
                                                [1]
                                                    @notification
                                                    .{Dict/get}
                                                        message
                                                    .{=}
                                                        You can only chat with partners that have a dedicated user.
                                                [2]
                                                    should display the correct information in the notification
            @testEnv
            .{Record/insert}
                [Record/models]
                    res.partner
                [res.partner/id]
                    14
            @testEnv
            .{Record/insert}
                [Record/models]
                    Server
                [Server/data]
                    @record
                    .{Test/data}
            @testEnv
            .{Env/openChat}
                [partnerId]
                    14
`;
