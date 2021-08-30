/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Test
        [Test/name]
            inbox: mark all messages as read
        [Test/model]
            DiscussComponent
        [Test/assertions]
            8
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
                [0]
                    [Record/models]
                        mail.channel
                    [mail.channel/id]
                        20
                [1]
                    {Dev/comment}
                        first expected message
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
                    [mail.message/needaction]
                        true
                    [mail.message/res_id]
                        20
                [2]
                    {Dev/comment}
                        second expected message
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
                    [mail.message/needaction]
                        true
                    [mail.message/res_id]
                        20
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
            {Test/assert}
                []
                    @testEnv
                    .{Env/inbox}
                    .{Thread/discussSidebarCategoryItemComponents}
                    .{Collection/first}
                    .{DiscussSidebarCategoryItemComponent/counter}
                    .{web.Element/textContent}
                    .{=}
                        2
                []
                    inbox should have counter of 2
            {Test/assert}
                []
                    @testEnv
                    .{Record/findById}
                        [Thread/id]
                            20
                        [Thread/model]
                            mail.channel
                    .{Thread/discussSidebarCategoryItemComponents}
                    .{Collection/first}
                    .{web.Element/textContent}
                    .{=}
                        2
                []
                    channel should have counter of 2
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
                    should have 2 messages in inbox
            {Test/assert}
                []
                    @testEnv
                    .{Record/all}
                        [Record/models]
                            ThreadViewTopbarComponent
                    .{Collection/first}
                    .{ThreadViewTopbarComponent/markAllReadButton}
                    .{web.Element/isDisabled}
                    .{isFalsy}
                []
                    should have enabled button 'Mark all read' in the top bar of inbox (has messages)

            @testEnv
            .{Component/afterNextRender}
                @testEnv
                .{UI/click}
                    @testEnv
                    .{Discuss/thread}
                    .{Thread/threadViews}
                    .{Collection/first}
                    .{ThreadView/threadViewTopbar}
                    .{ThreadViewTopbar/threadViewTopbarComponents}
                    .{Collection/first}
                    .{ThreadViewTopbarComponent/markAllReadButton}
            {Test/assert}
                []
                    @testEnv
                    .{Env/inbox}
                    .{Thread/discussSidebarCategoryItemComponents}
                    .{Collection/first}
                    .{DiscussSidebarCategoryItemComponent/counter}
                    .{isFalsy}
                []
                    inbox should display no counter (= 0)
            {Test/assert}
                []
                    @testEnv
                    .{Record/findById}
                        [Thread/id]
                            20
                        [Thread/model]
                            mail.channel
                    .{Thread/discussSidebarCategoryItemComponents}
                    .{Collection/first}
                    .{DiscussSidebarCategoryItemComponent/counter}
                    .{isFalsy}
                []
                    channel should display no counter (= 0)
            {Test/assert}
                []
                    @testEnv
                    .{Discuss/thread}
                    .{Thread/cache}
                    .{ThreadCache/messages}
                    .{Collection/length}
                    .{=}
                        0
                []
                    should have no message in inbox
            {Test/assert}
                []
                    @testEnv
                    .{Record/all}
                        [Record/models]
                            ThreadViewTopbarComponent
                    .{Collection/first}
                    .{ThreadViewTopbarComponent/markAllReadButton}
                    .{web.Element/isDisabled}
                []
                    should have disabled button 'Mark all read' in the top bar of inbox (no messages)
`;
