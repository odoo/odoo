/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Test
        [Test/name]
            messaging not initialized
        [Test/model]
            MessagingMenuComponent
        [Test/assertions]
            2
        [Test/scenario]
            :testEnv
                {Record/insert}
                    [Record/models]
                        Env
                    [Env/waitUntilMessagingCondition]
                        created
            @testEnv
            .[Record/insert]
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
                                    {Dev/comment}
                                        simulate messaging never initialized
                                    {Promise/await}
                                @original
            @testEnv
            .{Record/insert}
                [Record/models]
                    MessagingMenuComponent
            {Test/assert}
                []
                    @testEnv
                    .{MessagingMenu/messagingMenuComponents}
                    .{Collection/first}
                    .{MessagingMenuComponent/loading}
                []
                    should display loading icon on messaging menu when messaging not yet initialized

            @testEnv
            .{Component/afterNextRender}
                @testEnv
                .{UI/click}
                    @testEnv
                    .{MessagingMenu/messagingMenuComponents}
                    .{Collection/first}
                    .{MessagingMenuComponent/toggler}
            {Test/assert}
                []
                    @testEnv
                    .{MessagingMenu/messagingMenuComponents}
                    .{Collection/first}
                    .{MessagingMenuComponent/dropdownLoadingLabel}
                []
                    should prompt loading when opening messaging menu
`;
