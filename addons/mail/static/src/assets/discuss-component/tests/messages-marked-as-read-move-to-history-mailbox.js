/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Test
        [Test/name]
            messages marked as read move to "History" mailbox
        [Test/model]
            DiscussComponent
        [Test/assertions]
            10
        [Test/scenario]
            {Dev/comment}
                channel expected to be found in the sidebar
                with a random unique id that will be referenced in the test
            :testEnv
                {Record/insert}
                    [Record/models]
                        Env
            @testEnv
            .{Record/insert}
                [0]
                    [Record/models]
                        mail.channel
                    [mail.channel/id]
                        20
                [1]
                    {Dev/comment}
                        expected messages
                    [Record/models]
                        mail.message
                    [mail.message/body]
                        not empty
                    [mail.message/id]
                        100
                        {Dev/comment}
                            random unique id, useful to link notification
                    [mail.message/model]
                        mail.channel
                        {Dev/comment}
                            value to link message to channel
                    [mail.message/needaction]
                        true
                    [mail.message/res_id]
                        20
                        {Dev/comment}
                            id of related channel
                [2]
                    [Record/models]
                        mail.message
                    [mail.message/body]
                        not empty
                    [mail.message/id]
                        101
                        {Dev/comment}
                            random unique id, useful to link notification
                    [mail.message/model]
                        mail.channel
                        {Dev/comment}
                            value to link message to channel
                    [mail.message/needaction]
                        true
                    [mail.message/res_id]
                        20
                        {Dev/comment}
                            id of related channel
                [3]
                    {Dev/comment}
                        notification to have first message in inbox
                    [Record/models]
                        mail.notification
                    [mail.notification/notification_type]
                        inbox
                    [mail.notification/mail_message_id]
                        100
                        {Dev/comment}
                            id of related message
                    [mail.notification/res_partner_id]
                        @record
                        .{Test/data}
                        .{Data/currentPartnerId}
                        {Dev/comment}
                            must be for current partner
                [4]
                    {Dev/comment}
                        notification to have second message in inbox
                    [Record/models]
                        mail.notification
                    [mail.notification/notification_type]
                        inbox
                    [mail.notification/mail_message_id]
                        101
                        {Dev/comment}
                            id of related message
                    [mail.notification/res_partner_id]
                        @record
                        .{Test/data}
                        .{Data/currentPartnerId}
                        {Dev/comment}
                            must be for current partner
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
            @testEnv
            .{Thread/open}
                @testEnv
                .{Record/findById}
                    [Thread/id]
                        history
                    [Thread/model]
                        mail.box
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
                    should have empty thread in history

            @testEnv
            .{Component/afterNextRender}
                @testEnv
                .{UI/click}
                    @testEnv
                    .{Env/inbox}
                    .{Thread/discussSidebarCategoyItemComponents}
                    .{Collection/first}
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
                    .{isFalsy}
                []
                    inbox mailbox should not be empty
            {Test/assert}
                []
                    @testEnv
                    .{Discuss/thread}
                    .{Thread/cache}
                    .{ThreadCache/messages}
                    .{Collection/length}
                    .{=}
                        2
                []
                    inbox mailbox should have 2 messages

            @testEnv
            .{Component/afterNextRender}
                @testEnv
                .{UI/click}
                    @testEnv
                    .{Record/all}
                        [Record/models]
                            ThreadViewTopbarComponent
                    .{Collection/first}
                    .{ThreadViewTopbarComponent/markAllReadButton}
            {Test/assert}
                []
                    @testEnv
                    .{Discuss/thread}
                    .{=}
                        @testEnv
                        .{Env/inbox}
                []
                    inbox mailbox should still be active after mark as read
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
                    inbox mailbox should now be empty after mark as read

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
                    history mailbox should be active
            {Test/assert}
                []
                    @testEnv
                    .{Discuss/thread}
                    .{Thread/threadViews}
                    .{Collection/first}
                    .{ThreadView/messageListComponents}
                    .{Collection/first}
                    .{MessageListComponent/empty}
                    .{isFalsy}
                []
                    history mailbox should not be empty after mark as read
            {Test/assert}
                []
                    @testEnv
                    .{Discuss/thread}
                    .{Thread/cache}
                    .{ThreadCache/messages}
                    .{Collection/length}
                    .{=}
                        2
                []
                    history mailbox should have 2 messages
`;
