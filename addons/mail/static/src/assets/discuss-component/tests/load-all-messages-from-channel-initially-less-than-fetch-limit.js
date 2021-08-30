/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Test
        [Test/name]
            load all messages from channel initially, less than fetch limit (29 < 30)
        [Test/model]
            DiscussComponent
        [Test/assertions]
            5
        [Test/scenario]
            {Dev/comment}
                AKU TODO: thread specific test
                channel expected to be rendered, with a random unique id
                that will be referenced in the test
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
                        partner to be set as author, with a random unique
                        id that will be used to link message
                    [Record/models]
                        res.partner
                    [res.partner/id]
                            11
                {foreach}
                    {Record/insert}
                        [Record/models]
                            Range
                        [start]
                            29
                        [end]
                            0
                .{as}
                    i
                .{do}
                    {entry}
                        [Record/models]
                            mail.message
                        [mail.message/body]
                            not empty
                        [mail.message/date]
                            2019-04-20 10:00:00
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
                        [Function/out]
                            {if}
                                @route
                                .{=}
                                    /mail/channel/messages
                            .{then}
                                {Test/assert}
                                    [0]
                                        @record
                                    [1]
                                        @args
                                        .{Dict/get}
                                            limit
                                        .{=}
                                            30
                                    [2]
                                        should fetch up to 30 messages
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
                    .{Discuss/thread}
                    .{Thread/threadViews}
                    .{Collection/first}
                    .{ThreadView/messageListComponents}
                    .{Collection/first}
                    .{MessageListComponent/separatorDate}
                []
                    should have a single date separator
                    {Dev/comment}
                        to check: may be client timezone dependent
            {Test/assert}
                []
                    @testEnv
                    .{Discuss/thread}
                    .{Thread/threadViews}
                    .{Collection/first}
                    .{ThreadView/messageListComponents}
                    .{Collection/first}
                    .{MessageListComponent/separatorLabelDate}
                    .{web.Element/textContent}
                    .{=}
                        April 20, 2019
                []
                    should display date day of messages
            {Test/assert}
                []
                    @testEnv
                    .{Discuss/thread}
                    .{Thread/cache}
                    .{ThreadCache/messages}
                    .{Collection/length}
                    .{=}
                        29
                []
                    should have 29 messages
            {Test/assert}
                []
                    @testEnv
                    .{Discuss/thread}
                    .{Thread/threadViews}
                    .{Collection/first}
                    .{ThreadView/messageListComponents}
                    .{Collection/first}
                    .{MessageListComponent/loadMore}
                    .{isFalsy}
                []
                    should not have load more link
`;
