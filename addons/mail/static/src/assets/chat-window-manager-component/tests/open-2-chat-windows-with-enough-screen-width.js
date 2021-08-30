/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        computation uses following info:
        ([mocked] global window width: @see 'Env/create' action)
        (others: @see ChatWindowManager.visual)

        - chat window width: 325px
        - start/end/between gap width: 10px/10px/5px
        - hidden menu width: 200px
        - global width: 1920px

        Enough space for 2 visible chat windows:
         10 + 325 + 5 + 325 + 10 = 670 < 1920
    {Test}
        [Test/name]
            open 2 different chat windows: enough screen width
        [Test/model]
            ChatWindowManagerComponent
        [Test/isFocusRequired]
            true
        [Test/assertions]
            8
        [Test/scenario]
            {Dev/comment}
                2 channels are expected to be found in the messaging menu, each
                with a random unique id that will be referenced in the test
            :testEnv
                {Record/insert}
                    [Record/models]
                        Env
                    [Env/owlEnv]
                        [browser]
                            [innerWidth]
                                1920
                                {Dev/comment}
                                    enough to fit at least 2 chat windows
            @testEnv
            .{Record/insert}
                [0]
                    [Record/models]
                        mail.channel
                    [mail.channel/id]
                        10
                [1]
                    [Record/models]
                        mail.channel
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
                []
                    [Record/models]
                        ChatWindowManagerComponent
                []
                    [Record/models]
                        MessagingMenuComponent
            @testEnv
            .{Component/afterNextRender}
                @testEnv
                .{UI/click}
                    @testEnv
                    .{MessagingMenu/messagingMenuComponents}
                    .{Collection/first}
                    .{MessagingMenuComponent/toggler}
            @testEnv
            .{Component/afterNextRender}
                @testEnv
                .{UI/click}
                    @testEnv
                    .{Record/findById}
                        [Thread/id]
                            10
                        [Thread/model]
                            mail.channel
                    .{Thread/threadPreviewComponents}
                    .{Collection/first}
            {Test/assert}
                []
                    @testEnv
                    .{ChatWindowManager/chatWindowManagerComponents}
                    .{Collection/first}
                    .{ChatWindowManagerComponent/chatWindows}
                    .{Collection/length}
                    .{=}
                        1
                []
                    should have open a chat window
            {Test/assert}
                []
                    @testEnv
                    .{Record/findById}
                        [Thread/id]
                            10
                        [Thread/model]
                            mail.channel
                    .{Thread/chatWindows}
                    .{Collection/first}
                    .{ChatWindow/isVisible}
                []
                    chat window of chat should be open
            {Test/assert}
                []
                    @testEnv
                    .{Record/findById}
                        [Thread/id]
                            10
                        [Thread/model]
                            mail.channel
                    .{Thread/chatWindows}
                    .{Collection/first}
                    .{ChatWindow/isFocused}
                []
                    chat window of chat should have focus

            @testEnv
            .{Component/afterNextRender}
                @testEnv
                .{UI/click}
                    @testEnv
                    .{MessagingMenu/messagingMenuComponents}
                    .{Collection/first}
                    .{MessagingMenuComponent/toggler}
            @testEnv
            .{Component/afterNextRender}
                @testEnv
                .{UI/click}
                    @testEnv
                    .{Record/findById}
                        [Thread/id]
                            20
                        [Thread/model]
                            mail.channel
                    .{Thread/threadPreviewComponents}
                    .{Collection/first}
            {Test/assert}
                []
                    @testEnv
                    .{ChatWindowManager/chatWindowManagerComponents}
                    .{Collection/first}
                    .{ChatWindowManagerComponent/chatWindows}
                    .{Collection/length}
                    .{=}
                        2
                []
                    should have open a new chat window
            {Test/assert}
                []
                    @testEnv
                    .{Record/findById}
                        [Thread/id]
                            20
                        [Thread/model]
                            mail.channel
                    .{Thread/chatWindows}
                    .{Collection/first}
                    .{ChatWindow/isVisible}
                []
                    chat window of channel should be open
            {Test/assert}
                []
                    @testEnv
                    .{Record/findById}
                        [Thread/id]
                            10
                        [Thread/model]
                            mail.channel
                    .{Thread/chatWindows}
                    .{Collection/first}
                    .{ChatWindow/isVisible}
                []
                    chat window of chat should still be open
            {Test/assert}
                []
                    @testEnv
                    .{Record/findById}
                        [Thread/id]
                            20
                        [Thread/model]
                            mail.channel
                    .{Thread/chatWindows}
                    .{Collection/first}
                    .{ChatWindow/isFocused}
                []
                    chat window of channel should have focus
            {Test/assert}
                []
                    @testEnv
                    .{Record/findById}
                        [Thread/id]
                            10
                        [Thread/model]
                            mail.channel
                    .{Thread/chatWindows}
                    .{Collection/first}
                    .{ChatWindow/isFocused}
                    .{isFalsy}
                []
                    chat window of chat should no longer have focus
`;
