/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        computation uses following info:
        ([mocked] global window width: 900px)
        (others: @see ChatWindowManager/visual)

        - chat window width: 325px
        - start/end/between gap width: 10px/10px/5px
        - hidden menu width: 200px
        - global width: 1080px

        Enough space for 2 visible chat windows, and one hidden chat window:
        3 visible chat windows:
         10 + 325 + 5 + 325 + 5 + 325 + 10 = 1000 > 900
        2 visible chat windows + hidden menu:
         10 + 325 + 5 + 325 + 10 + 200 + 5 = 875 < 900
    {Test}
        [Test/name]
            does not fetch messages if hidden
        [Test/model]
            ChatWindowManagerComponent
        [Test/assertions]
            11
        [Test/scenario]
            {Dev/comment}
                3 channels are expected to be found in the messaging menu, each
                with a random unique id that will be referenced in the test
            :testEnv
                {Record/insert}
                    [Record/models]
                        Env
                    [Env/browser]
                        [Browser/innerWidth]
                            900
            @testEnv
            .{Record/insert}
                [0]
                    [Record/models]
                        mail.channel
                    [mail.channel/id]
                        10
                    [mail.channel/is_minimized]
                        true
                    [mail.channel/name]
                        Channel #10
                    [mail.channel/state]
                        open
                [1]
                    [Record/models]
                        mail.channel
                    [mail.channel/id]
                        11
                    [mail.channel/is_minimized]
                        true
                    [mail.channel/name]
                        Channel #11
                    [mail.channel/state]
                        open
                [2]
                    [Record/models]
                        mail.channel
                    [mail.channel/id]
                        12
                    [mail.channel/is_minimized]
                        true
                    [mail.channel/name]
                        Channel #12
                    [mail.channel/state]
                        open
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
                                    /mail/channel/messages
                            .{then}
                                {Test/step}
                                    rpc:/mail/channel/messages:
                                    .{+}
                                        @args
                                        .{Dict/get}
                                            channel_id
                            @original
            @testEnv
            .{Record/insert}
                [Record/models]
                    ChatWindowManagerComponent
            {Test/assert}
                []
                    @testEnv
                    .{ChatWindowManager/chatWindowManagerComponents}
                    .{Collection/first}
                    .{ChatWindowManangerComponent/chatWindows}
                    .{Collection/length}
                    .{=}
                        2
                []
                    2 chat windows should be visible
            {Test/assert}
                []
                    @testEnv
                    .{Record/findById}
                        [Thread/id]
                            12
                        [Thread/model]
                            mail.channel
                    .{Thread/chatWindows}
                    .{Collection/first}
                    .{ChatWindow/isVisible}
                    .{isFalsy}
                []
                    chat window for Channel #12 should be hidden
            {Test/assert}
                []
                    @testEnv
                    .{ChatWindowManager/chatWindowManagerComponents}
                    .{Collection/first}
                    .{ChatWindowManagerComponent/hiddenMenu}
                []
                    chat window hidden menu should be displayed
            {Test/verifySteps}
                []
                    rpc:/mail/channel/messages:10
                    rpc:/mail/channel/messages:11
                []
                    messages should be fetched for the two visible chat windows

            @testEnv
            .{Component/afterNextRender}
                @testEnv
                .{UI/click}
                    @testEnv
                    .{ChatWindowManager/chatWindowManagerComponents}
                    .{Collection/first}
                    .{ChatWindowManagerComponent/hiddenMenu}
                    .{ChatWindowHiddenMenuComponent/dropdownToggle}
            {Test/assert}
                []
                    @testEnv
                    .{ChatWindowManager/chatWindowManagerComponents}
                    .{Collection/first}
                    .{ChatWindowManagerComponent/hiddenMenu}
                    .{ChatWindowHiddenMenuComponent/chatWindowHeaders}
                    .{Collection/length}
                    .{=}
                        1
                []
                    1 hidden chat window should be listed in hidden menu

            @testEnv
            .{Component/afterNextRender}
                @testEnv
                .{UI/click}
                    @testEnv
                    .{ChatWindowManager/chatWindowManagerComponents}
                    .{Collection/first}
                    .{ChatWindowManagerComponent/hiddenMenu}
                    .{ChatWindowHiddenMenuComponent/chatWindowHeaders}
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
                    2 chat windows should still be visible
            {Test/assert}
                []
                    @testEnv
                    .{Record/findById}
                        [Thread/id]
                            12
                        [Thread/model]
                            mail.channel
                    .{Thread/chatWindows}
                    .{Collection/first}
                    .{ChatWindow/isVisible}
                []
                    chat window for Channel #12 should now be visible
            {Test/verifySteps}
                []
                    rpc:/mail/channel/messages:12
                []
                    messages should now be fetched for Channel #12
`;
