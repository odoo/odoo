/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Test
        [Test/name]
            simplest layout of a not followed subtype
        [Test/model]
            FollowerSubtypeComponent
        [Test/assertions]
            5
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
            :followerSubtype
                @testEnv
                .{Record/insert}
                    [Record/models]
                        FollowerSubtype
                    [FollowerSubtype/id]
                        1
                    [FollowerSubtype/isDefault]
                        true
                    [FollowerSubtype/isInternal]
                        false
                    [FollowerSubtype/name]
                        Dummy test
                    [FollowerSubtype/resModel]
                        res.partner
            @testEnv
            .{Record/update}
                [0]
                    @follower
                [1]
                    [Follower/subtypes]
                        @testEnv
                        .{Field/add}
                            @followerSubtype
            @testEnv
            .{Record/insert}
                [Record/models]
                    FollowerSubtypeComponent
                [FollowerSubtypeComponent/follower]
                    @follower
                [FollowerSubtypeComponent/followerSubtype]
                    @followerSubtype
            {Test/assert}
                []
                    @testEnv
                    .{Record/all}
                        [Record/models]
                            FollowerSubtypeComponent
                    .{Collection/length}
                    .{=}
                        1
                []
                    should have follower subtype component
            {Test/assert}
                []
                    @testEnv
                    .{Record/all}
                        [Record/models]
                            FollowerSubtypeComponent
                    .{Collection/first}
                    .{FollowerSubtypeComponent/label}
                []
                    should have a label
            {Test/assert}
                []
                    @testEnv
                    .{Record/all}
                        [Record/models]
                            FollowerSubtypeComponent
                    .{Collection/first}
                    .{FollowerSubtypeComponent/checkbox}
                []
                    should have a checkbox
            {Test/assert}
                []
                    @testEnv
                    .{Record/all}
                        [Record/models]
                            FollowerSubtypeComponent
                    .{Collection/first}
                    .{FollowerSubtypeComponent/label}
                    .{web.Element/textContent}
                    .{=}
                        Dummy test
                []
                    should have the name of the subtype as label
            {Test/assert}
                []
                    @testEnv
                    .{Record/all}
                        [Record/models]
                            FollowerSubtypeComponent
                    .{Collection/first}
                    .{FollowerSubtypeComponent/checkbox}
                    .{web.Element/isChecked}
                    .{isFalsy}
                []
                    checkbox should not be checked as follower subtype is not followed
`;
