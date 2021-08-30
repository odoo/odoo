/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Test
        [Test/name]
            messaging becomes initialized
        [Test/model]
            DiscussComponent
        [Test/assertions]
            2
        [Test/scenario]
            :messagingInitialized
                {Record/insert}
                    [Record/models]
                        Deferred
            :testEnv
                {Record/insert}
                    [Record/models]
                        Env
                    [Env/waitUntilMessagingCondition]
                        created
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
                                @route
                                .{=}
                                    /mail/init_messaging
                            .{then}
                                {Promise/await}
                                    @messagingInitialized
                            @original
            @testEnv
            .{Record/insert}
                [Record/models]
                    DiscussComponent
            {Test/assert}
                []
                    @testEnv
                    .{DiscussContainerComponent/spinner}
                []
                    should display messaging not initialized

            @testEnv
            .{Component/afterNextRender}
                {Promise/resolve}
                    @messagingInitialized
            {Test/assert}
                []
                    @testEnv
                    .{DiscussContainerComponent/spinner}
                    .{isFalsy}
                []
                    should no longer display messaging not initialized
`;
