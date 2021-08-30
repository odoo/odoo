/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Test
        [Test/name]
            mark channel as seen on last message visible
        [Test/model]
            DiscussComponent
        [Test/isFocusRequired: true
        [Test/assertions]
            3
        [Test/scenario]
            {Dev/comment}
                channel expected to be found in the sidebar, with the expected
                message_unread_counter and a random unique id that will be
                referenced in the test
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
                        10
                    [mail.channel/message_unread_counter]
                        1
                [1]
                    [Record/models]
                        mail.message
                    [mail.message/body]
                        not empty
                    [mail.message/id]
                        12
                    [mail.message/model]
                        mail.channel
                    [mail.message/res_id]
                        10
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
                    .{Record/findById}
                        [Thread/id]
                            10
                        [Thread/model]
                            mail.channel
                    .{Thread/discussSidebarCategoryItemComponents}
                    .{Collection/length}
                    .{=}
                        1
                []
                    should have discuss sidebar item with the channel
            {Test/assert}
                []
                    @testEnv
                    .{Record/findById}
                        [Thread/id]
                            10
                        [Thread/model]
                            mail.channel
                    .{Thread/localMessageUnreadCounter}
                    .{>}
                        0
                []
                    sidebar item of channel ID 10 should be unread

            @testEnv
            .{Component/afterNextRender}
                @testEnv
                .{UI/afterEvent}
                    [eventName]
                        o-thread-last-seen-by-current-partner-message-id-changed
                    [func]
                        @testEnv
                        .{UI/click}
                            @testEnv
                            .{Record/findById}
                                [Thread/id]
                                    10
                                [Thread/model]
                                    mail.channel
                            .{Thread/discussSidebarCategoryItemComponents}
                            .{Collection/first}
                    [message]
                        should wait until last seen by current partner message id changed
                    [predicate]
                        {Record/insert}
                            [Record/models]
                                Function
                            [Function/in]
                                thread
                            [Function/out]
                                @thread
                                .{Thread/id}
                                .{=}
                                    10
                                .{&}
                                    @thread
                                    .{Thread/model}
                                    .{=}
                                        mail.channel
                                .{&}
                                    @thread
                                    .{Thread/lastSeenByCurrentPartnerMessageId}
                                    .{=}
                                        12
            {Test/assert}
                []
                    @testEnv
                    .{Record/findById}
                        [Thread/id]
                            10
                        [Thread/model]
                            mail.channel
                    .{Thread/localMessageUnreadCounter}
                    .{=}
                        0
                []
                    sidebar item of channel ID 10 should not longer be unread
`;
