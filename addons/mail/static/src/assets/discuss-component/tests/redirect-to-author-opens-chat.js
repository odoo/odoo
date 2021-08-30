/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Test
        [Test/name]
            redirect to author opens chat
        [Test/model]
            DiscussComponent
        [Test/assertions]
            5
        [Test/scenario]
            :testEnv
                {Record/insert}
                    [Record/models]
                        Env
            @testEnv
            .{Record/insert}
                [0]
                    {Dev/comment}
                        channel expected to be found in the sidebar
                    [Record/models]
                        mail.channel
                    [mail.channel/id]
                        1
                        {Dev/comment}
                            random unique id, will be referenced in the test
                    [mail.channel/name]
                        General
                        {Dev/comment}
                            random name, will be asserted in the test
                [1]
                    {Dev/comment}
                        chat expected to be found in the sidebar
                    [Record/models]
                        mail.channel
                    [mail.channel/channel_type]
                        chat
                        {Dev/comment}
                            testing a chat is the goal of the test
                    [mail.channel/id]
                        10
                        {Dev/comment}
                            random unique id, will be referenced in the test
                    [mail.channel/members]
                        {Dev/comment}
                            expected partners
                        [0]
                            @record
                            .{Test/data}
                            .{Data/currentPartnerId}
                        [1]
                            7
                    [mail.channel/public]
                        private
                        {Dev/comment}
                            expected value for testing a chat
                [2]
                    [Record/models]
                        mail.message
                    [mail.message/author_id]
                        7
                    [mail.message/body]
                        not empty
                    [mail.message/id]
                        100
                    [mail.message/model]
                        mail.channel
                    [mail.message/res_id]
                        1
                [3]
                    {Dev/comment}
                        expected correspondent, with a random unique id
                        that will be used to link partner to chat and
                        a random name that will be asserted in the test
                    [Record/models]
                        res.partner
                    [res.partner/id]
                        7
                    [res.partner/name]
                        Demo
                [4]
                    [Record/models]
                        res.users
                    [res.users/partner_id]
                        7
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
                        1
                    [Thread/model]
                        mail.channel
            {Test/assert}
                []
                    @testEnv
                    .{Discuss/thread}
                    .{=}
                        @testEnv
                        .{Record/findById}
                            [Thread/id]
                                1
                            [Thread/model]
                                mail.channel
                []
                    channel 'General' should be active
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
                    should have 1 message
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
                    message1 should have author image
            {Test/assert}
                []
                    @testEnv
                    .{Record/findById}
                        [Message/id]
                            100
                    .{Message/messageComponents}
                    .{Collection/first}
                    .{MessageViewComponent/authorAvatar}
                    .{web.Element/class}
                    .{String/includes}
                        o_redirect
                []
                    message1 should have redirect to author

            @testEnv
            .{Component/afterNextRender}
                @testEnv
                .{UI/click}
                    @testEnv
                    .{Record/findById}
                        [Message/id]
                            100
                    .{Message/messageComponents}
                    .{Collection/first}
                    .{MessageViewComponent/authorAvatar}
            {Test/assert}
                []
                    @testEnv
                    .{Discuss/thread}
                    .{=}
                        @testEnv
                        .{Record/findById}
                            [Thread/id]
                                10
                            [Thread/model]
                                mail.channel
                []
                    chat 'Demo' should become active after author redirection
`;
