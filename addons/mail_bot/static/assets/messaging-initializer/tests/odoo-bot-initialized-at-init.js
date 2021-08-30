/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Test
        [Test/name]
            OdooBot initialized at init
        [Test/feature]
            mail_bot
        [Test/model]
            MessagingInitializer
        [Test/assertions]
            2
        [Test/scenario]
            {Dev/comment}
                TODO this test should be completed in combination with
                implementing _mockMailChannelInitOdooBot task-2300480
            :testEnv
                {Record/insert}
                    [Record/models]
                        Env
                    [Env/owlEnv]
                        [session]
                            [odoobot_initialized]
                                false
            @testEnv
            .{Record/insert}
                [Record/models]
                    Server
                [Server/data]
                    @record
                    .{Test/data}
                [Server/mockRPC]
                    {Record/insert}
                        [Record/models]
                            Function
                        [Function/in]
                            route
                            args
                            original
                        [Function/out]
                            {if}
                                @args
                                .{Dict/get}
                                    method
                                .{=}
                                    init_odoobot
                            .{then}
                                {Test/step}
                                    init_odoobot
                            @original
            {Test/verifySteps}
                []
                    init_odoobot
                []
                    should have initialized OdooBot at init
`;
