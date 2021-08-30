/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Test
        [Test/name]
            basic top bar rendering
        [Test/model]
            DiscussComponent
        [Test/assertions]
            8
        [Test/scenario]
            {Dev/comment}
                channel expected to be found in the sidebar
                with a random unique id and name that will be referenced in the test
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
                [mail.channel/name]
                    General
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
                    .{Discuss/thread}
                    .{Thread/threadViews}
                    .{Collection/first}
                    .{ThreadView/threadViewTopbar}
                    .{ThreadViewTopbar/threadViewTopbarComponents}
                    .{Collection/first}
                    .{ThreadViewTopbarComponent/thread}
                    .{web.Element/textContent}
                    .{=}
                        Inbox
                []
                    display inbox in the top bar
            {Test/assert}
                []
                    @testEnv
                    .{Discuss/thread}
                    .{Thread/threadViews}
                    .{Collection/first}
                    .{ThreadView/threadViewTopbar}
                    .{ThreadViewTopbar/threadViewTopbarComponents}
                    .{Collection/first}
                    .{ThreadViewTopbarComponent/markAllReadButton}
                []
                    should have visible button 'Mark all read' in the top bar of inbox
            {Test/assert}
                []
                    @testEnv
                    .{Discuss/thread}
                    .{Thread/threadViews}
                    .{Collection/first}
                    .{ThreadView/threadViewTopbar}
                    .{ThreadViewTopbar/threadViewTopbarComponents}
                    .{Collection/first}
                    .{ThreadViewTopbarComponent/markAllReadButton}
                    .{web.Element/isDisabled}
                []
                    should have disabled button 'Mark all read' in the topbar of inbox (no messages)

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
                    .{Thread/threadViews}
                    .{Collection/first}
                    .{ThreadView/threadViewTopbar}
                    .{ThreadViewTopbar/threadViewTopbarComponents}
                    .{Collection/first}
                    .{ThreadViewTopbarComponent/threadName}
                    .{web.Element/textContent}
                    .{=}
                        Starred
                []
                    display starred in the top bar
            {Test/assert}
                []
                    @testEnv
                    .{Discuss/thread}
                    .{Thread/threadViews}
                    .{Collection/first}
                    .{ThreadView/threadViewTopbar}
                    .{ThreadViewTopbar/threadViewTopbarComponents}
                    .{Collection/first}
                    .{ThreadViewTopbarComponent/unstarAllButton}
                []
                    should have visible button 'Unstar all' in the top bar of starred
            {Test/assert}
                []
                    @testEnv
                    .{Discuss/thread}
                    .{Thread/threadViews}
                    .{Collection/first}
                    .{ThreadView/threadViewTopbar}
                    .{ThreadViewTopbar/threadViewTopbarComponents}
                    .{Collection/first}
                    .{ThreadViewTopbarComponent/unstarAllButton}
                    .{web.Element/isDisabled}
                []
                    should have disabled button 'Unstar all' in the top bar of starred (no messages)

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
                    .{Thread/discussSidebarCategoryItemComponent}
                    .{Collection/first}
            {Test/assert}
                []
                    @testEnv
                    .{Discuss/thread}
                    .{Thread/threadViews}
                    .{Collection/first}
                    .{ThreadView/threadViewTopbar}
                    .{ThreadViewTopbar/threadViewTopbarComponents}
                    .{Collection/first}
                    .{web.Element/textContent}
                    .{=}
                        #General
                []
                    display general in the breadcrumb
            {Test/assert}
                []
                    @testEnv
                    .{Discuss/thread}
                    .{Thread/threadViews}
                    .{Collection/first}
                    .{ThreadView/threadViewTopbar}
                    .{ThreadViewTopbar/threadViewTopbarComponents}
                    .{Collection/first}
                    .{ThreadViewTopbarComponent/inviteButton}
                []
                    should have button 'Invite' in the top bar of channel
`;
