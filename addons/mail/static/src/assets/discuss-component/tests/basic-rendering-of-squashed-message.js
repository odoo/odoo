/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Test
        [Test/name]
            basic rendering of squashed message
        [Test/model]
            DiscussComponent
        [Test/assertions]
            10
        [Test/scenario]
            {Dev/comment}
                messages are squashed when "close", e.g. less than 1 minute has
                elapsed from messages of same author and same thread. Note that
                this should be working in non-mailboxes
                AKU TODO: should be message and/or message list-only tests
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
                        {Dev/comment}
                            must be same author as other message
                    [mail.message/body]
                        <p>body1</p>
                        {Dev/comment}
                            random body, set for consistency
                    [mail.message/date]
                        2019-04-20 10:00:00
                        {Dev/comment}
                            date must be within 1 min from other message
                    [mail.message/id]
                        100
                        {Dev/comment}
                            random unique id, will be referenced in the test
                    [mail.message/message_type]
                        comment
                        {Dev/comment}
                            must be a squash-able type-
                    [mail.message/model]
                        mail.channel
                        {Dev/comment}
                            to link message to channel
                    [mail.message/res_id]
                        20
                        {Dev/comment}
                            id of related channel
                [2]
                    [Record/models]
                        mail.message
                    [mail.message/author_id]
                        11
                        {Dev/comment}
                            must be same author as other message
                    [mail.message/body]
                        <p>body2</p>
                        {Dev/comment}
                            random body, will be asserted in the test
                    [mail.message/date]
                        2019-04-20 10:00:30
                        {Dev/comment}
                            date must be within 1 min from other message
                    [mail.message/id]
                        101
                        {Dev/comment}
                            random unique id, will be referenced in the test
                    [mail.message/message_type]
                        comment
                        {Dev/comment}
                            must be a squash-able type
                    [mail.message/model]
                        mail.channel
                        {Dev/comment}
                            to link message to channel
                    [mail.message/res_id]
                        20
                        {Dev/comment}
                            id of related channel
                [3]
                    {Dev/comment}
                        partner to be set as author, with a random unique id
                        that will be used to link message
                    [Record/models]
                        res.partner
                    [res.partner/id]
                        11
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
                    .{Discuss/thread}
                    .{Thread/cache}
                    .{ThreadCache/messages}
                    .{Collection/length}
                    .{=}
                        2
                []
                    should have 2 messages
            {Test/assert}
                []
                    @testEnv
                    .{Record/findById}
                        [Message/id]
                            100
                    .{Message/messageComponents}
                    .{Collection/first}
                    .{MessageViewComponent/isSquashed}
                    .{isFalsy}
                []
                    message 1 should not be squashed
            {Test/assert}
                []
                    @testEnv
                    .{Record/findById}
                        [Message/id]
                            101
                    .{Message/messageComponents}
                    .{Collection/first}
                    .{MessageViewComponent/isSquashed}
                []
                    message 2 should be squashed

            @testEnv
            .{UI/click}
                @testEnv
                .{Record/findById}
                    [Message/id]
                        101
                .{Message/messageComponents}
                .{Collection/first}
            {Test/assert}
                []
                    @testEnv
                    .{Record/findById}
                        [Message/id]
                            101
                    .{Message/messageComponents}
                    .{Collection/first}
                    .{MessageViewComponent/dateSquashed}
                []
                    message 2 should have date in sidebar
            {Test/assert}
                []
                    @testEnv
                    .{Record/findById}
                        [Message/id]
                            101
                    .{Message/actionList}
                    .{MessageActionList/messageActionListComponents}
                    .{Collection/length}
                    .{=}
                        1
                []
                    message 2 should have some actions
            {Test/assert}
                []
                    @testEnv
                    .{Record/findById}
                        [Message/id]
                            101
                    .{Message/actionList}
                    .{MessageActionList/messageActionListComponents}
                    .{Collection/first}
                    .{MessageActionListComponent/actionStar}
                []
                    message 2 should have star action in action list
            {Test/assert}
                []
                    @testEnv
                    .{Record/findById}
                        [Message/id]
                            101
                    .{Message/messageComponents}
                    .{Collection/first}
                    .{MessageViewComponent/core}
                []
                    message 2 should have core part
            {Test/assert}
                []
                    @testEnv
                    .{Record/findById}
                        [Message/id]
                            101
                    .{Message/messageComponents}
                    .{Collection/first}
                    .{MessageViewComponent/header}
                    .{isFalsy}
                []
                    message 2 should have a header in core part
            {Test/assert}
                []
                    @testEnv
                    .{Record/findById}
                        [Message/id]
                            101
                    .{Message/messageComponents}
                    .{Collection/first}
                    .{MessageViewComponent/content}
                []
                    message 2 should have some content in core part
            {Test/assert}
                []
                    @testEnv
                    .{Record/findById}
                        [Message/id]
                            101
                    .{Message/messageComponents}
                    .{Collection/first}
                    .{MessageViewComponent/content}
                    .{web.Element/textContent}
                    .{=}
                        body2
                []
                    message 2 should have body in content part
`;
