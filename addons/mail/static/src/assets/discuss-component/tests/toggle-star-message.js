/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Test
        [Test/name]
            toggle star message
        [Test/model]
            DiscussComponent
        [Test/assertions]
            16
        [Test/scenario]
            :testEnv
                {Record/insert}
                    [Record/models]
                        Env
            @testEnv
            .{Record/insert}
                {Dev/comment}
                    channel expected to be initially rendered
                    with a random unique id, will be referenced in the test
                [0]
                    [Record/models]
                        mail.channel
                    [mail.channel/id]
                        20
                [1]
                    [Record/models]
                        mail.message
                    [mail.message/body]
                        not empty
                    [mail.message/id]
                        100
                    [mail.message/model]
                        mail.channel
                    [mail.message/res_id]
                        20
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
                                @args
                                .{Dict/get}
                                    method
                                .{=}
                                    toggle_message_starred
                            .{then}
                                {Test/step}
                                    rpc:toggle_message_starred
                                {Test/assert}
                                    []
                                        @args
                                        .{Dict/get}
                                            args
                                        .{Collection/first}
                                        .{Collection/first}
                                        .{=}
                                            100
                                    []
                                        should have message Id in args
                            @original
            @testEnv
            .{Record/insert}
                [Record/models]
                    DiscussComponent
            @testEnv
            .{Thread/open}
                @testEnv
                .{Record/findById}
                    [Thread/id]
                        20
                    [Thread/model]
                        mail.channel
            {Test/assert}
                []
                    @testEnv
                    .{Env/starred}
                    .{Thread/discussSidebarCategoryItemComponents}
                    .{Collection/first}
                    .{DiscussSidebarCategoryItemComponent/counter}
                    .{isFalsy}
                []
                    starred should display no counter (= 0)
            {Test/assert}
                []
                    @testEnv
                    .{Discuss/thread}
                    .{Thread/cache}
                    .{ThreadCache/messages}
                    .{Collection/length}
                    .{=}
                        1
                []
                    should have 1 message in channel
            {Test/assert}
                []
                    @testEnv
                    .{Record/findById}
                        [Message/id]
                            100
                    .{Message/isStarred}
                    .{isFalsy}
                []
                    message should not be starred

            @testEnv
            .{UI/click}
                @testEnv
                .{Record/findById}
                    [Message/id]
                        100
                .{Message/messageComponents}
                .{Collection/first}
            {Test/assert}
                []
                    @testEnv
                    .{Discuss/thread}
                    .{Thread/cache}
                    .{ThreadCache/messages}
                    .{Collection/first}
                    .{Message/actionList}
                    .{MessageActionList/messageActionListComponents}
                    .{Collection/first}
                    .{MessageActionListComponent/actionStar}
                []
                    message should have star action

            @testEnv
            .{Component/afterNextRender}
                @testEnv
                .{UI/click}
                    @testEnv
                    .{Discuss/thread}
                    .{Thread/cache}
                    .{ThreadCache/messages}
                    .{Collection/first}
                    .{Message/actionList}
                    .{MessageActionList/messageActionListComponents}
                    .{Collection/first}
                    .{MessageActionListComponent/actionStar}
            {Test/verifySteps}
                rpc:toggle_message_starred
            {Test/assert}
                []
                    @testEnv
                    .{Env/starred}
                    .{Thread/discussSidebarCategoryItemComponents}
                    .{Collection/first}
                    .{DiscussSidebarCategoryItemComponent/counter}
                    .{web.Element/textContent}
                    .{=}
                        1
                []
                    starred should display a counter of 1
            {Test/assert}
                []
                    @testEnv
                    .{Discuss/thread}
                    .{Thread/cache}
                    .{ThreadCache/messages}
                    .{Collection/length}
                    .{=}
                        1
                []
                    should have kept 1 message in channel
            {Test/assert}
                []
                    @testEnv
                    .{Record/findById}
                        [Message/id]
                            100
                    .{Message/isStarred}
                []
                    message should be starred

            @testEnv
            .{Component/afterNextRender}
                @testEnv
                .{UI/click}
                    @testEnv
                    .{Discuss/thread}
                    .{Thread/cache}
                    .{ThreadCache/messages}
                    .{Collection/first}
                    .{Message/actionList}
                    .{MessageActionList/messageActionListComponents}
                    .{Collection/first}
                    .{MessageActionListComponent/actionStar}
            {Test/verifySteps}
                rpc:toggle_message_starred
            {Test/assert}
                []
                    @testEnv
                    .{Env/starred}
                    .{Thread/discussSidebarCategoryItemComponents}
                    .{Collection/first}
                    .{DiscussSidebarCategoryItemComponent/counter}
                    .{isFalsy}
                []
                    starred should no longer display a counter (= 0)
            {Test/assert}
                []
                    @testEnv
                    .{Discuss/thread}
                    .{Thread/cache}
                    .{ThreadCache/messages}
                    .{Collection/length}
                    .{=}
                        1
                []
                    should still have 1 message in channel
            {Test/assert}
                []
                    @testEnv
                    .{Record/findById}
                        [Message/id]
                            100
                    .{Message/isStarred}
                    .{isFalsy}
                []
                    message should no longer be starred
`;
