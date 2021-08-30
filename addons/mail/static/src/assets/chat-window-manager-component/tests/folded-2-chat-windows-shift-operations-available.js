/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        computation uses following info:
        ([mocked] global window width: 900px)
        (others: @see ChatWindowManager/visual)

        - chat window width: 325px
        - start/end/between gap width: 10px/10px/5px
        - global width: 900px

        2 visible chat windows + hidden menu:
         10 + 325 + 5 + 325 + 10 = 675 < 900
    {Test}
        [Test/name]
            folded 2 chat windows: check shift operations are available
        [Test/model]
            ChatWindowManagerComponent
        [Test/assertions]
            13
        [Test/scenario]
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
                    [mail.channel/channel_type]
                        channel
                    [mail.channel/is_minimized]
                        true
                    [mail.channel/is_pinned]
                        true
                    [mail.channel/state]
                        folded
                [1]
                    [Record/models]
                        mail.channel
                    [mail.channel/channel_type]
                        chat
                    [mail.channel/is_minimized]
                        true
                    [mail.channel/is_pinned]
                        true
                    [mail.channel/members]
                        [0]
                            @record
                            .{Test/data}
                            .{Data/currentPartnerId}
                        [1]
                            7
                    [mail.channel/state]
                        folded
                [2]
                    [Record/models]
                        res.partner
                    [res.partner/id]
                        7
                    [res.partner/name]
                        Demo
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
                    should have opened 2 chat windows initially
            {Test/assert}
                []
                    @testEnv
                    .{ChatWindowManager/chatWindows}
                    .{Collection/first}
                    .{ChatWindow/isFolded}
                []
                    first chat window should be folded
            {Test/assert}
                []
                    @testEnv
                    .{ChatWindowManager/chatWindows}
                    .{Collection/second}
                    .{ChatWindow/isFolded}
                []
                    second chat window should be folded
            {Test/assert}
                []
                    @testEnv
                    .{ChatWindowManager/chatWindows}
                    .{Collection/second}
                    .{ChatWindow/chatWindowComponents}
                    .{Collection/first}
                    .{ChatWindowComponent/commandShiftPrev}
                []
                    there should be only one chat window allowed to shift left even if folded
            {Test/assert}
                []
                    @testEnv
                    .{ChatWindowManager/chatWindows}
                    .{Collection/first}
                    .{ChatWindow/chatWindowComponents}
                    .{Collection/first}
                    .{ChatWindowComponent/commandShiftNext}
                []
                    there should be only one chat window allowed to shift right even if folded

            :initialFirstChatWindow
                @testEnv
                .{ChatWindowManager/chatWindows}
                .{Collection/first}
            :initialSecondChatWindow
                @testEnv
                .{ChatWindowManager/chatWindows}
                .{Collection/second}
            @testEnv
            .{Component/afterNextRender}
                @testEnv
                .{UI/click}
                    @testEnv
                    .{ChatWindowManager/chatWindows}
                    .{Collection/second}
                    .{ChatWindow/chatWindowComponents}
                    .{Collection/first}
                    .{ChatWindowComponent/commandShiftPrev}
            {Test/assert}
                []
                    @testEnv
                    .{ChatWindowManager/chatWindows}
                    .{Collection/first}
                    .{=}
                        @initialSecondChatWindow
                []
                    First chat window should be second after it has been shift left
            {Test/assert}
                []
                    @testEnv
                    .{ChatWindowManager/chatWindows}
                    .{Collection/second}
                    .{=}
                        @initialFirstChatWindow
                []
                    Second chat window should be first after the first has been shifted left

            @testEnv
            .{Component/afterNextRender}
                @testEnv
                .{UI/click}
                    @testEnv
                    .{ChatWindowManager/chatWindows}
                    .{Collection/second}
                    .{ChatWindow/chatWindowComponents}
                    .{Collection/first}
                    .{ChatWindowComponent/commandShiftPrev}
            {Test/assert}
                []
                    @testEnv
                    .{ChatWindowManager/chatWindows}
                    .{Collection/first}
                    .{=}
                        @initialFirstChatWindow
                []
                    First chat window should be back at first place
            {Test/assert}
                []
                    @testEnv
                    .{ChatWindowManager/chatWindows}
                    .{Collection/second}
                    .{=}
                        @initialSecondChatWindow
                []
                    Second chat window should be back at second place

            @testEnv
            .{Component/afterNextRender}
                @testEnv
                .{UI/click}
                    @testEnv
                    .{ChatWindowManager/chatWindows}
                    .{Collection/first}
                    .{ChatWindow/chatWindowHeaderComponents}
                    .{Collection/first}
                    .{ChatWindowComponent/commandShiftNext}
            {Test/assert}
                []
                    @testEnv
                    .{ChatWindowManager/chatWindows}
                    .{Collection/first}
                    .{=}
                        @initialSecondChatWindow
                []
                    First chat window should be second after it has been shift right
            {Test/assert}
                []
                    @testEnv
                    .{ChatWindowManager/chatWindows}
                    .{Collection/second}
                    .{=}
                        @initialFirstChatWindow
                []
                    Second chat window should be first after the first has been shifted right

            @testEnv
            .{Component/afterNextRender}
                @testEnv
                .{UI/click}
                    @testEnv
                    .{ChatWindowManager/chatWindows}
                    .{Collection/first}
                    .{ChatWindow/chatWindowHeaderComponents}
                    .{Collection/first}
                    .{ChatWindowHeaderComponent/commandShiftNext}
            {Test/assert}
                []
                    @testEnv
                    .{ChatWindowManager/chatWindows}
                    .{Collection/first}
                    .{=}
                        @initialFirstChatWindow
                []
                    First chat window should be back at first place
            {Test/assert}
                []
                    @testEnv
                    .{ChatWindowManager/chatWindows}
                    .{Collection/second}
                    .{=}
                        @initialSecondChatWindow
                []
                    Second chat window should be back at second place
`;
