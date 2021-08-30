/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Test
        [Test/name]
            default thread rendering
        [Test/model]
            DiscussComponent
        [Test/assertions]
            16
        [Test/scenario]
            {Dev/comment}
                channel expected to be found in the sidebar,
                with a random unique id that will be referenced in the test
            :testEnv
                {Record/insert}
                    [Record/models]
                        Env
            @testEnv
            .{Record/insert}
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
                [Record/models]
                    DiscussComponent
            {Test/assert}
                []
                    @testEnv
                    .{Env/inbox}
                    .{Thread/discussSidebarCategoryItemComponents}
                    .{Collection/length}
                    .{=}
                        1
                []
                    should have inbox mailbox in the sidebar
            {Test/assert}
                []
                    @testEnv
                    .{Env/starred}
                    .{Thread/discussSidebarCategoryItemComponents}
                    .{Collection/length}
                    .{=}
                        1
                []
                    should have starred mailbox in the sidebar
            {Test/assert}
                []
                    @testEnv
                    .{Env/history}
                    .{Thread/discussSidebarCategoryItemComponents}
                    .{Collection/length}
                    .{=}
                        1
                []
                    should have history mailbox in the sidebar
            {Test/assert}
                []
                    @testEnv
                    .{Record/findById}
                        [Thread/id]
                            20
                        [Thread/model]
                            mail.channel
                    .{Thread/discussSidebarCategoryItemComponents}
                    .{Collection/length}
                    .{=}
                        1
                []
                    should have channel 20 in the sidebar
            {Test/assert}
                []
                    @testEnv
                    .{Discuss/thread}
                    .{=}
                        @testEnv
                        .{Env/inbox}
                []
                    inbox mailbox should be active thread
            {Test/assert}
                []
                    @testEnv
                    .{Discuss/thread}
                    .{Thread/threadViews}
                    .{Collection/first}
                    .{ThreadView/messageListComponents}
                    .{Collection/first}
                    .{MessageListComponent/empty}
                []
                    should have empty thread in inbox
            {Test/assert}
                @testEnv
                .{Discuss/thread}
                .{Thread/threadViews}
                .{Collection/first}
                .{ThreadView/messageListComponents}
                .{Collection/first}
                .{MessageListComponent/empty}
                .{web.Element/textContent}
                .{=}
                    Congratulations, your inbox is empty  New messages appear here.

            @testEnv
            .{Component/afterNextRender}
                @testEnv
                .{UI/click}
                    @testEnv
                    .{Env/starred}
                    .{Thread/discussSidebarCategoryItemComponents}
                    .{Collection/first}
            {Test/assert}
                []
                    @testEnv
                    .{Discuss/thread}
                    .{=}
                        @testEnv
                        .{Env/starred}
                []
                    starred mailbox should be active thread
            {Test/assert}
                []
                    @testEnv
                    .{Discuss/thread}
                    .{Thread/threadViews}
                    .{Collection/first}
                    .{ThreadView/messageListComponents}
                    .{Collection/first}
                    .{MessageListComponent/empty}
                []
                    should have empty thread in starred
            {Test/assert}
                @testEnv
                .{Discuss/thread}
                .{Thread/threadViews}
                .{Collection/first}
                .{ThreadView/messageListComponents}
                .{Collection/first}
                .{MessageListComponent/empty}
                .{web.Element/textContent}
                .{=}
                    No starred messages  You can mark any message as 'starred', and it shows up in this mailbox.

            @testEnv
            .{Component/afterNextRender}
                @testEnv
                .{UI/click}
                    @testEnv
                    .{Env/history}
                    .{Thread/discussSidebarCategoryItemComponents}
                    .{Collection/first}
            {Test/assert}
                []
                    @testEnv
                    .{Discuss/thread}
                    .{=}
                        @testEnv
                        .{Env/history}
                []
                    history mailbox should be active thread
            {Test/assert}
                []
                    @testEnv
                    .{Discuss/thread}
                    .{Thread/threadViews}
                    .{Collection/first}
                    .{ThreadView/messageListComponents}
                    .{Collection/first}
                    .{MessageListComponent/empty}
                []
                    should have empty thread in starred
            {Test/assert}
                @testEnv
                .{Discuss/thread}
                .{Thread/threadViews}
                .{Collection/first}
                .{ThreadView/messageListComponents}
                .{Collection/first}
                .{MessageListComponent/empty}
                .{web.Element/textContent}
                .{=}
                    No history messages  Messages marked as read will appear in the history.

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
                    .{Thread/discussSidebarCategoryItemComponents}
                    .{Collection/first}
            {Test/assert}
                []
                    @testEnv
                    .{Discuss/thread}
                    .{=}
                        @testEnv
                        .{Record/findById}
                            [Thread/id]
                                20
                            [Thread/model]
                                mail.channel
                []
                    channel 20 should be active thread
            {Test/assert}
                []
                    @testEnv
                    .{Discuss/thread}
                    .{Thread/threadViews}
                    .{Collection/first}
                    .{ThreadView/messageListComponents}
                    .{Collection/first}
                    .{MessageListComponent/empty}
                []
                    should have empty thread in channel
            {Test/assert}
                @testEnv
                .{Discuss/thread}
                .{Thread/threadViews}
                .{Collection/first}
                .{ThreadView/messageListComponents}
                .{Collection/first}
                .{MessageListComponent/empty}
                .{web.Element/textContent}
                .{=}
                    There are no messages in this conversation.
`;
