/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        InnerWith computation uses following info:
        ([mocked] global window width: @see 'Env/create' action)
        (others: @see 'ChatWindowManager/visual')

        - chat window width: 325px
        - start/end/between gap width: 10px/10px/5px
        - hidden menu width: 200px
        - global width: 1920px

        Enough space for 3 visible chat windows:
         10 + 325 + 5 + 325 + 5 + 325 + 10 = 1000 < 1920
    {Test}
        [Test/name]
            TAB cycle with 3 open chat windows
        [Test/model]
            ChatWindowManagerComponent
        [Test/isFocusRequired]
            true
        [Test/assertions]
            6
        [Test/scenario]
            {Dev/comment}
                Note: in LTR, chat windows are placed from right to left. TAB cycling
                should move from left to right in this configuration, therefore cycling
                moves to following lower index.
            :testEnv
                {Record/insert}
                    [Record/models]
                        Env
                    [Env/owlEnv]
                        [browser]
                            [innerWidth]
                                1920
            @testEnv
            .{Record/insert}
                [0]
                    [Record/models]
                        mail.channel
                    [mail.channel/is_minimized]
                        true
                    [mail.channel/is_pinned]
                        true
                    [mail.channel/state]
                        open
                [1]
                    [Record/models]
                        mail.channel
                    [mail.channel/is_minimized]
                        true
                    [mail.channel/is_pinned]
                        true
                    [mail.channel/state]
                        open
                [2]
                    [Record/models]
                        mail.channel
                    [mail.channel/is_minimized]
                        true
                    [mail.channel/is_pinned]
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
                        3
                []
                    initialy, 3 chat windows should be present
            {Test/assert}
                []
                    @testEnv
                    .{ChatWindowManager/chatWindowManagerComponents}
                    .{Collection/first}
                    .{ChatWindowManagerComponent/chatWindows}
                    .{Collection/length}
                    .{=}
                        3
                []
                    all 3 chat windows should be open (unfolded)

            @testEnv
            .{Component/afterNextRender}
                @testEnv
                .{UI/focus}
                    @testEnv
                    .{ChatWindowManager/chatWindows}
                    .{Collection/third}
                    .{ChatWindow/thread}
                    .{Thread/composer}
                    .{Composer/composerTextInputComponents}
                    .{Collection/first}
                    .{ComposerTextInputComponent/textarea}
            {Test/assert}
                []
                    @testEnv
                    .{ChatWindowManager/chatWindows}
                    .{Collection/third}
                    .{ChatWindow/thread}
                    .{Thread/composer}
                    .{Composer/composerTextInputComponents}
                    .{Collection/first}
                    .{ComposerTextInputComponent/textarea}
                    .{=}
                        @testEnv
                        .{web.Browser/document}
                        .{web.Document/activeElement}
                []
                    The 3rd chat window should have the focus

            @testEnv
            .{Component/afterNextRender}
                @testEnv
                .{UI/keydown}
                    [0]
                        @testEnv
                        .{ChatWindowManager/chatWindows}
                        .{Collection/third}
                        .{ChatWindow/thread}
                        .{Thread/composer}
                        .{Composer/composerTextInputComponents}
                        .{Collection/first}
                        .{ComposerTextInputComponent/textarea}
                    [1]
                        [key]
                            Tab
            {Test/assert}
                []
                    @testEnv
                    .{ChatWindowManager/chatWindows}
                    .{Collection/second}
                    .{ChatWindow/thread}
                    .{Thread/composer}
                    .{Composer/composerTextInputComponents}
                    .{Collection/first}
                    .{ComposerTextInputComponent/textarea}
                    .{=}
                        @testEnv
                        .{web.Browser/document}
                        .{web.Document/activeElement}
                []
                    after pressing tab on the 3rd chat window, the 2nd chat window should have focus

            @testEnv
            .{Component/afterNextRender}
                @testEnv
                .{UI/keydown}
                    [0]
                        @testEnv
                        .{ChatWindowManager/chatWindows}
                        .{Collection/second}
                        .{ChatWindow/thread}
                        .{Thread/composer}
                        .{Composer/composerTextInputComponents}
                        .{Collection/first}
                        .{ComposerTextInputComponent/textarea}
                    [1]
                        [key]
                            Tab
            {Test/assert}
                []
                    @testEnv
                    .{ChatWindowManager/chatWindows}
                    .{Collection/first}
                    .{ChatWindow/thread}
                    .{Thread/composer}
                    .{Composer/composerTextInputComponents}
                    .{Collection/first}
                    .{ComposerTextInputComponent/textarea}
                    .{=}
                        @testEnv
                        .{web.Browser/document}
                        .{web.Document/activeElement}
                []
                    after pressing tab on the 2nd chat window, the 1st chat window should have focus

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
                        [key]
                            Tab
            {Test/assert}
                []
                    @testEnv
                    .{ChatWindowManager/chatWindows}
                    .{Collection/third}
                    .{ChatWindow/thread}
                    .{Thread/composer}
                    .{Composer/composerTextInputComponents}
                    .{Collection/first}
                    .{ComposerTextInputComponent/textarea}
                    .{=}
                        @testEnv
                        .{web.Browser/document}
                        .{web.Document/activeElement}
                []
                    the 3rd chat window should have the focus after pressing tab on the 1st chat window
`;
