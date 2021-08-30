/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Test
        [Test/name]
            new message: fold
        [Test/model]
            ChatWindowManagerComponent
        [Test/assertions]
            6
        [Test/scenario]
            :testEnv
                {Record/insert}
                    [Record/models]
                        Env
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
                    .{MessagingMenu/messagingMenuComponents}
                    .{Collection/first}
                    .{MessagingMenuComponent/newMessageButton}
            {Test/assert}
                []
                    @testEnv
                    .{ChatWindowManager/newMessageChatWindow}
                    .{ChatWindow/isFolded}
                    .{isFalsy}
                []
                    chat window should not be folded by default
            {Test/assert}
                []
                    @testEnv
                    .{ChatWindowManager/newMessageChatWindow}
                    .{ChatWindow/chatWindowComponents}
                    .{Collection/first}
                    .{ChatWindowComponent/newMessageForm}
                []
                    chat window should have new message form

            @testEnv
            .{Component/afterNextRender}
                @testEnv
                .{UI/click}
                    @testEnv
                    .{ChatWindowManager/newMessageChatWindow}
                    .{ChatWindow/chatWindowHeaderComponents}
                    .{Collection/first}
            {Test/assert}
                []
                    @testEnv
                    .{ChatWindowManager/newMessageChatWindow}
                    .{ChatWindow/isFolded}
                []
                    chat window should become folded
            {Test/assert}
                []
                    @testEnv
                    .{ChatWindowManager/newMessageChatWindow}
                    .{ChatWindow/chatWindowComponents}
                    .{Collection/first}
                    .{ChatWindowComponent/newMessageForm}
                    .{isFalsy}
                []
                    chat window should not have new message form

            @testEnv
            .{Component/afterNextRender}
                @testEnv
                .{UI/click}
                    @testEnv
                    .{ChatWindowManager/newMessageChatWindow}
                    .{ChatWindow/chatWindowHeaderComponents}
                    .{Collection/first}
            {Test/assert}
                []
                    @testEnv
                    .{ChatWindowManager/newMessageChatWindow}
                    .{ChatWindow/isFolded}
                    .{isFalsy}
                []
                    chat window should become unfolded
            {Test/assert}
                []
                    @testEnv
                    .{ChatWindowManager/newMessageChatWindow}
                    .{ChatWindow/chatWindowComponents}
                    .{Collection/first}
                    .{ChatWindowComponent/newMessageForm}
                []
                    chat window should have new message form
`;
