/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Test
        [Test/name]
            basic rendering of message
        [Test/model]
            DiscussComponent
        [Test/assertions]
            15
        [Test/scenario]
            {Dev/comment}
                AKU TODO: should be in message-only tests
                channel expected to be rendered, with a random unique id that
                will be referenced in the test
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
                    [Record/models]
                        mail.message
                    [mail.message/author_id]
                        11
                    [mail.message/body]
                        <p>body</p>
                    [mail.message/date]
                        2019-04-20 10:00:00
                    [mail.message/id]
                        100
                    [mail.message/model]
                        mail.channel
                    [mail.message/res_id]
                        20
                [2]
                    {Dev/comment}
                        partner to be set as author, with a random unique id
                        that will be used to link message and a random name
                        that will be asserted in the test
                    [Record/models]
                        res.partner
                    [res.partner/id]
                        11
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
                    .{Record/findById}
                        [Message/id]
                            100
                    .{Message/messageComponents}
                    .{Collection/first}
                    .{MessageViewComponent/sidebar}
                []
                    should have message sidebar of message
            {Test/assert}
                []
                    @testEnv
                    .{Record/findById}
                        [Message/id]
                            100
                    .{Message/messageComponents}
                    .{Collection/first}
                    .{MessageViewComponent/authorAvatar}
                []
                    should have author avatar in sidebar of message
            {Test/assert}
                []
                    @testEnv
                    .{Record/findById}
                        [Message/id]
                            100
                    .{Message/messageComponents}
                    .{Collection/first}
                    .{MessageViewComponent/authorAvatar}
                    .{web.Element/src}
                    .{=}
                        /mail/channel/20/partner/11/avatar_128
                []
                    should have url of message in author avatar sidebar
            {Test/assert}
                []
                    @testEnv
                    .{Record/findById}
                        [Message/id]
                            100
                    .{Message/messageComponents}
                    .{Collection/first}
                    .{MessageViewComponent/core}
                []
                    should have core part of message
            {Test/assert}
                []
                    @testEnv
                    .{Record/findById}
                        [Message/id]
                            100
                    .{Message/messageComponents}
                    .{Collection/first}
                    .{MessageViewComponent/header}
                []
                    should have header in core part of message
            {Test/assert}
                []
                    @testEnv
                    .{Record/findById}
                        [Message/id]
                            100
                    .{Message/messageComponents}
                    .{Collection/first}
                    .{MessageViewComponent/authorName}
                []
                    should have author name in header of message
            {Test/assert}
                []
                    @testEnv
                    .{Record/findById}
                        [Message/id]
                            100
                    .{Message/messageComponents}
                    .{Collection/first}
                    .{MessageViewComponent/authorName}
                    .{web.Element/textContent}
                    .{=}
                        Demo
                []
                    should have textually author name in header of message
            {Test/assert}
                []
                    @testEnv
                    .{Record/findById}
                        [Message/id]
                            100
                    .{Message/messageComponents}
                    .{Collection/first}
                    .{MessageViewComponent/headerDate}
                []
                    should have date in header of message

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
                    .{Record/findById}
                        [Message/id]
                            100
                    .{Message/actionList}
                    .{MessageActionList/messageActionListComponents}
                    .{Collection/length}
                    .{=}
                        1
                []
                    should have action list in header of message
            {Test/assert}
                []
                    @testEnv
                    .{Record/findById}
                        [Message/id]
                            100
                    .{Message/actionList}
                    .{MessageActionList/messageActionListComponents}
                    .{Collection/first}
                    .{MessageActionListComponent/action}
                    .{Collection/length}
                    .{=}
                        3
                []
                    should have 3 actions in action list of message
            {Test/assert}
                []
                    @testEnv
                    .{Record/findById}
                        [Message/id]
                            100
                    .{Message/actionList}
                    .{MessageActionList/messageActionListComponents}
                    .{Collection/first}
                    .{MessageActionListComponent/actionStar}
                []
                    should have action to star message
            {Test/assert}
                []
                    @testEnv
                    .{Record/findById}
                        [Message/id]
                            100
                    .{Message/actionList}
                    .{MessageActionList/messageActionListComponents}
                    .{Collection/first}
                    .{MessageActionListComponent/actionReaction}
                []
                    should have action to add a reaction
            {Test/assert}
                []
                    @testEnv
                    .{Record/findById}
                        [Message/id]
                            100
                    .{Message/actionList}
                    .{MessageActionList/messageActionListComponents}
                    .{Collection/first}
                    .{MessageActionListComponent/actionReply}
                []
                    should have action to reply to message
            {Test/assert}
                []
                    @testEnv
                    .{Record/findById}
                        [Message/id]
                            100
                    .{Message/messageComponents}
                    .{Collection/first}
                    .{MessageViewComponent/content}
                []
                    should have content in core part of message
            {Test/assert}
                []
                    @testEnv
                    .{Record/findById}
                        [Message/id]
                            100
                    .{Message/messageComponents}
                    .{Collection/first}
                    .{MessageViewComponent/content}
                    .{web.Element/textContent}
                    .{=}
                        body
                []
                    should have body of message in content part of message
`;
