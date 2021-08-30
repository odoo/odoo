/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        computation uses following info:
        ([mocked] global window width: 900px)
        (others: @see 'ChatWindowManager/visual')

        - chat window width: 325px
        - start/end/between gap width: 10px/10px/5px
        - hidden menu width: 200px
        - global width: 1080px

        Enough space for 2 visible chat windows, and one hidden chat window:
        3 visible chat windows:
         10 + 325 + 5 + 325 + 5 + 325 + 10 = 1000 < 900
        2 visible chat windows + hidden menu:
         10 + 325 + 5 + 325 + 10 + 200 + 5 = 875 < 900
    {Test}
        [Test/name]
            open 3 different chat windows: not enough screen width
        [Test/model]
            ChatWindowManagerComponent
        [Test/assertions]
            12
        [Test/scenario]
            {Dev/comment}
                3 channels are expected to be found in the messaging menu, each
                with a random unique id that will be referenced in the test
            :testEnv
                {Record/insert}
                    [Record/insert]
                        Env
                    [Env/owlEnv]
                        [browser]
                            [innerWidth]
                                900
                                {Dev/comment}
                                    enough to fit 2 chat windows but not 3
            @testEnv
            .{Record/insert}
                [0]
                    [Record/models]
                        mail.channel
                    [mail.channel/id]
                        1
                [1]
                    [Record/models]
                        mail.channel
                    [mail.channel/id]
                        2
                [2]
                    [Record/models]
                        mail.channel
                    [mail.channel/id]
                        3
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
            {Dev/comment}
                open, from systray menu, chat windows of channels
                with Id 1, 2, then 3
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
                            1
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
                    .{ChatWindowComponent/length}
                    .{=}
                        1
                []
                    should have open 1 visible chat window
            {Test/assert}
                []
                    @testEnv
                    .{ChatWindowManager/chatWindowManagerComponents}
                    .{Collection/first}
                    .{ChatWindowManagerComponent/hiddenMenu}
                    .{isFalsy}
                []
                    should not have hidden menu
            {Test/assert}
                []
                    @testEnv
                    .{MessagingMenu/messagingMenuComponents}
                    .{Collection/first}
                    .{MessagingMenuComponent/dropdownMenu}
                    .{isFalsy}
                []
                    messaging menu should be hidden

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
                            2
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
                    should have open 2 visible chat windows
            {Test/assert}
                []
                    @testEnv
                    .{ChatWindowManager/chatWindowManagerComponents}
                    .{Collection/first}
                    .{ChatWindowManagerComponent/hiddenMenu}
                    .{isFalsy}
                []
                    should not have hidden menu
            {Test/assert}
                []
                    @testEnv
                    .{MessagingMenu/messagingMenuComponents}
                    .{Collection/first}
                    .{MessagingMenuComponent/dropdownMenu}
                    .{isFalsy}
                []
                    messaging menu should be hidden

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
                            3
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
                [2]
                    should have open 2 visible chat windows
            {Test/assert}
                []
                    @testEnv
                    .{ChatWindowManager/chatWindowManagerComponents}
                    .{Collection/first}
                    .{ChatWindowManagerComponent/hiddenMenu}
                []
                    should have hidden menu
            {Test/assert}
                []
                    @testEnv
                    .{MessagingMenu/messagingMenuComponents}
                    .{Collection/first}
                    .{MessagingMenuComponent/dropdownMenu}
                    .{isFalsy}
                []
                    messaging menu should be hidden
            {Test/assert}
                []
                    @testEnv
                    .{Record/findById}
                        [Thread/id]
                            1
                        [Thread/model]
                            mail.channel
                    .{Thread/chatWindows}
                    .{Collection/first}
                    .{ChatWindow/chatWindowComponents}
                    .{Collection/first}
                    .{ChatWindowComponent/isVisible}
                [2]
                    chat window of channel 1 should be open
            {Test/assert}
                []
                    @testEnv
                    .{Record/findById}
                        [Thread/id]
                            3
                        [Thread/model]
                            mail.channel
                    .{Thread/chatWindows}
                    .{Collection/first}
                    .{ChatWindow/chatWindowComponents}
                    .{Collection/first}
                    .{ChatWindowComponent/isVisible}
                []
                    chat window of channel 3 should be open
            {Test/assert}
                []
                    @testEnv
                    .{Record/findById}
                        [Thread/id]
                            3
                        [Thread/model]
                            mail.channel
                    .{Thread/chatWindows}
                    .{Collection/first}
                    .{ChatWindow/isFocused}
                []
                    chat window of channel 3 should have focus
`;
