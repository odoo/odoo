/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Test
        [Test/name]
            base rendering editable
        [Test/model]
            FollowerComponent
        [Test/assertions]
            6
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
            :follower
                @testEnv
                .{Record/insert}
                    [Record/models]
                        Follower
                    [Follower/followedThread]
                        @thread
                    [Follower/id]
                        2
                    [Follower/isActive]
                        true
                    [Follower/isEditable]
                        true
                    [Follower/partner]
                        @testEnv
                        .{Record/insert}
                            [Record/models]
                                Partner
                            [Partner/id]
                                1
                            [Partner/name]
                                François Perusse
            @testEnv
            .{Record/insert}
                [Record/models]
                    FollowerComponent
                [FollowerComponent/follower]
                    @follower
            {Test/assert}
                []
                    @follower
                    .{Follower/followerComponents}
                    .{Collection/length}
                    .{=}
                        1
                []
                    should have follower component
            {Test/assert}
                []
                    @follower
                    .{Follower/followerComponents}
                    .{Collection/first}
                    .{FollowerComponent/details}
                []
                    should display a details part
            {Test/assert}
                []
                    @follower
                    .{Follower/followerComponents}
                    .{Collection/first}
                    .{FollowerComponent/avatar}
                []
                    should display the avatar of the follower
            {Test/assert}
                []
                    @follower
                    .{Follower/followerComponents}
                    .{Collection/first}
                    .{FollowerComponent/name}
                []
                    should display the name of the follower
            {Test/assert}
                []
                    @follower
                    .{Follower/followerComponents}
                    .{Collection/first}
                    .{FollowerComponent/editButton}
                []
                    should have an edit button
            {Test/assert}
                []
                    @follower
                    .{Follower/followerComponents}
                    .{Collection/first}
                    .{FollowerComponent/removeButton}
                []
                    should have a remove button
`;
