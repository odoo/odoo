/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Test
        [Test/name]
            base rendering no attachment
        [Test/model]
            ChatterComponent
        [Test/assertions]
            6
        [Test/scenario]
            :testEnv
                {Record/insert}
                    [Record/models]
                        Env
            @testEnv
            .{Record/insert}
                [0]
                    [Record/models]
                        res.partner
                    [res.partner/id]
                        100
                {foreach}
                    {Record/insert}
                        [Record/models]
                            Range
                        [start]
                            0
                        [end]
                            60
                .{as}
                    i
                .{do}
                    {entry}
                        [Record/models]
                            mail.message
                        [mail.message/body]
                            not empty
                        [mail.message/model]
                            res.partner
                        [mail.message/res_id]
                            100
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
                    ChatterContainerComponent
                [ChatterContainerComponent/threadId]
                    100
                [ChatterContainerComponent/threadModel]
                    res.partner
            {Test/assert}
                []
                    @chatter
                    .{Chatter/chatterComponents}
                    .{Collection/length}
                    .{=}
                        1
                []
                    should have a chatter
            {Test/assert}
                []
                    @chatter
                    .{Chatter/chatterTopbarComponents}
                    .{Collection/length}
                    .{=}
                        1
                []
                    should have a chatter topbar
            {Test/assert}
                []
                    @chatter
                    .{Chatter/chatterComponents}
                    .{Collection/first}
                    .{ChatterComponent/attachmentBox}
                    .{isFalsy}
                []
                    should not have an attachment box in the chatter
            {Test/assert}
                []
                    @chatter
                    .{Chatter/chatterComponents}
                    .{Collection/first}
                    .{ChatterComponent/thread}
                []
                    should have a thread in the chatter
            {Test/assert}
                []
                    @chatter
                    .{Chatter/chatterComponents}
                    .{Collection/first}
                    .{ChatterComponent/thread}
                    .{=}
                        @testEnv
                        .{Record/findById}
                            [Thread/id]
                                100
                            [Thread/model]
                                res.partner
                        .{Thread/threadViews}
                        .{Collection/first}
                        .{ThreadView/threadViewComponents}
                        .{Collection/first}
                []
                    thread should have the right thread local id
            {Test/assert}
                []
                    @chatter
                    .{Chatter/thread}
                    .{Thread/cache}
                    .{ThreadCache/messages}
                    .{Collection/length}
                    .{=}
                        30
                []
                    the first 30 messages of thread should be loaded
`;
