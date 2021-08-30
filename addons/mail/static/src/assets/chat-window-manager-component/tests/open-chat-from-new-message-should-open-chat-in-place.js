/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        InnerWith computation uses following info:
        ([mocked] global window width: @see 'Env/create' action)
        (others: @see ChatWindowManager.visual)

        - chat window width: 325px
        - start/end/between gap width: 10px/10px/5px
        - hidden menu width: 200px
        - global width: 1920px

        Enough space for 3 visible chat windows:
         10 + 325 + 5 + 325 + 5 + 325 + 10 = 1000 < 1920
    {Test}
        [Test/name]
            open chat from "new message" chat window should open chat in place of this "new message" chat window
        [Test/model]
            ChatWindowManagerComponent
        [Test/assertions]
            11
        [Test/scenario]
            :imSearchDef
                {Record/insert}
                    [Record/models]
                        Deferred
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
                    [mail.channel/is_minimized]
                        true
                [1]
                    [Record/models]
                        res.partner
                    [res.partner/id]
                        131
                    [res.partner/name]
                        Partner 131
                [2]
                    [Record/models]
                        res.users
                    [res.users/partner_id]
                        131
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
                            :res
                                @original
                            {if}
                                @args
                                .{Dict/get}
                                    method
                                .{=}
                                    im_search
                            .{then}
                                {Promise/resolve}
                                    @imSearchDef
                            @res
            @testEnv
            .{Record/insert}
                []
                    [Record/models]
                        ChatWindowManagerComponent
                []
                    [Record/models]
                        MessagingMenuComponent
            {Test/assert}
                []
                    @testEnv
                    .{ChatWindowManager/chatWindows}
                    .{Collection/length}
                    .{=}
                        2
                []
                    should have 2 chat windows initially
            {Test/assert}
                []
                    @testEnv
                    .{ChatWindowManager/newMessageChatWindow}
                    .{isFalsy}
                []
                    should not have any 'new message' chat window initially

            {Dev/comment}
                open "new message" chat window
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
                    .{MessagingMenu/messagingMenuComponents}
                    .{Collection/first}
                    .{MessagingMenuComponent/newMessageButton}
            {Test/assert}
                []
                    @testEnv
                    .{ChatWindowManager/newMessageChatWindow}
                []
                    should have 'new message' chat window after clicking 'new message' in messaging menu
            {Test/assert}
                []
                    @testEnv
                    .{ChatWindowManager/chatWindows}
                    .{Collection/length}
                    .{=}
                        3
                []
                    should have 3 chat window after opening 'new message' chat window
            {Test/assert}
                []
                    @testEnv
                    .{ChatWindowManager/newMessageChatWindow}
                    .{ChatWindow/chatWindowComponents}
                    .{Collection/first}
                    .{ChatWindowComponent/newMessageFormInput}
                []
                    'new message' chat window should have new message form input
            {Test/assert}
                []
                    @testEnv
                    .{ChatWindowManager/newMessageChatWindow}
                    .{=}
                        @testEnv
                        .{ChatWindowManager/chatWindows}
                        .{Collection/third}
                []
                    'new message' chat window should be the last chat window initially

            @testEnv
            .{Component/afterNextRender}
                @testEnv
                .{UI/click}
                    @testEnv
                    .{ChatWindowManager/newMessageChatWindow}
                    .{ChatWindow/chatWindowHeaderComponents}
                    .{Collection/first}
                    .{ChatWindowHeaderComponent/commandShiftNext}
            {Test/assert}
                []
                    @testEnv
                    .{ChatWindowManager/newMessageChatWindow}
                    .{=}
                        @testEnv
                        .{ChatWindowManager/chatWindows}
                        .{Collection/second}
                []
                    'new message' chat window should have moved to the middle after clicking shift previous

            {Dev/comment}
                search for a user in "new message" autocomplete
            @testEnv
            .{UI/insertText}
                131
            @testEnv
            .{UI/keydown}
                @testEnv
                .{ChatWindowManager/newMessageChatWindow}
                .{ChatWindow/chatWindowComponents}
                .{Collection/first}
                .{ChatWindowComponent/newMessageFormInput}
            @testEnv
            .{UI/keyup}
                @testEnv
                .{ChatWindowManager/newMessageChatWindow}
                .{ChatWindow/chatWindowComponents}
                .{Collection/first}
                .{ChatWindowComponent/newMessageFormInput}
            {Dev/comment}
                Wait for search RPC to be resolved. The following await lines are
                necessary because autocomplete is an external lib therefore it is not
                possible to use 'afterNextRender'.
            {Promise/await}
                @imSearchDef
            {Utils/nextAnimationFrame}
            :link
                @testEnv
                .{web.Browser/document}
                .{web.Document/querySelector}
                    .ui-autocomplete
                    .ui-menu-item
                    a
            {Test/assert}
                []
                    @link
                []
                    should have autocomplete suggestion after typing on 'new message' input
            {Test/assert}
                []
                    @link
                    .{web.Element/textContent}
                    .{=}
                        Partner 131
                []
                    autocomplete suggestion should target the partner matching search term

            @testEnv
            .{Component/afterNextRender}
                @testEnv
                .{UI/click}
                    @link
            {Test/assert}
                []
                    @testEnv
                    .{ChatWindowManager/newMessageChatWindow}
                    .{isFalsy}
                []
                    should have removed the 'new message' chat window after selecting a partner
            {Test/assert}
                []
                    @testEnv
                    .{ChatWindowManager/chatWindows}
                    .{Collection/second}
                    .{ChatWindow/chatWindowHeaderComponents}
                    .{Collection/first}
                    .{ChatWindowHeaderComponent/name}
                    .{web.Element/textContent}
                    .{=}
                        Partner 131
                []
                    chat window with selected partner should be opened in position where 'new message' chat window was, which is in the middle
`;
