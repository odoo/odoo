/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Test
        [Test/name]
            base rendering not editable
        [Test/model]
            FollowButtonComponent
        [Test/assertions]
            3
        [Test/scenario]
            :testEnv
                {Record/insert}
                    [Record/models]
                        Env
            @testEnv
            .{Record/insert}
                [Record/models]
                    Server
                [Server/data]
                    @record
                    .{Test/data}
            :thread
                @testEnv
                .{Record/insert}
                    [Record/models]
                        Thread
                    [Thread/id]
                        100
                    [Thread/model]
                        res.partner
            @testEnv
            .{Record/insert}
                [Record/models]
                    FollowButtonComponent
                [FollowButtonComponent/isDisabled]
                    true
                [FollowButtonComponent/thread]
                    @thread
            {Test/assert}
                []
                    @thread
                    .{Thread/followButtonComponents}
                    .{Collection/length}
                    .{=}
                        1
                []
                    should have follow button component
            {Test/assert}
                []
                    @thread
                    .{Thread/followButtonComponents}
                    .{Collection/first}
                    .{FollowButtonComponent/follow}
                []
                    should have 'Follow' button
            {Test/assert}
                []
                    @thread
                    .{Thread/followButtonComponents}
                    .{Collection/first}
                    .{FollowButtonComponent/follow}
                    .{web.Element/isDisabled}
                []
                    'Follow' button should be disabled
`;
