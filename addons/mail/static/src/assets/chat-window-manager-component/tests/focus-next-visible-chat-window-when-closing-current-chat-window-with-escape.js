/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        computation uses following info:
        ([mocked] global window width: @see 'Env/create' action)
        (others: @see ChatWindowManager/visual)

        - chat window width: 325px
        - start/end/between gap width: 10px/10px/5px
        - hidden menu width: 200px
        - global width: 1920px

        Enough space for 2 visible chat windows:
         10 + 325 + 5 + 325 + 10 = 670 < 1920
    {Test}
        [Test/name]
            focus next visible chat window when closing current chat window with ESCAPE
        [Test/model]
            ChatWindowManagerComponent
        [Test/assertions]
            3
        [Test/isFocusRequired]
            true
        [Test/scenario]
            {Dev/comment}
                2 chat windows with thread are expected to be initially open for
                this test
            :testEnv
                {Record/insert}
                    [Record/models]
                        Env
                    [Env/browser]
                        [Browser/innerWidth]
                            1920
            @testEnv
            .{Record/insert}
                [0]
                    [Record/models]
                        mail.channel
                    [mail.channel/is_minimized]
                        true
                    [mail.channel/state]
                        open
                [1]
                    [Record/models]
                        mail.channel
                    [mail.channel/is_minimized]
                        true
                    [mail.channel/state]
                        open
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
                    ChatWindowManagerComponent
            {Test/assert}
                []
                    @testEnv
                    .{ChatWindowManager/chatWindows}
                    .{Collection/length}
                    .{=}
                        2
                []
                    2 chat windows should be present initially

            @testEnv
            .{Component/afterNextRender}
                @testEnv
                .{UI/keydown}
                    [0]
                        @testEnv
                        .{ChatWindowManager/chatWindows}
                        .{Collection/first}
                        .{ChatWindow/thread}
                        .{Thread/composer}
                        .{Composer/composerTextInputComponents}
                        .{Collection/first}
                        .{ComposerTextInputComponent/textarea}
                    [1]
                        [bubbles]
                            true
                        [key]
                            Escape
            {Test/assert}
                []
                    @testEnv
                    .{ChatWindowManager/chatWindows}
                    .{Collection/length}
                    .{=}
                        1
                []
                    only one chat window should remain after pressing escape on first chat window
            {Test/assert}
                []
                    @testEnv
                    .{ChatWindowManager/chatWindows}
                    .{Collection/first}
                    .{ChatWindow/isFocused}
                []
                    next visible chat window should be focused after pressing escape on first chat window
`;
