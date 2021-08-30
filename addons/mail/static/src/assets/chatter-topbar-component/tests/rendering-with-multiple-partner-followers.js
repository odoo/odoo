/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Test
        [Test/name]
            rendering with multiple partner followers
        [Test/model]
            ChatterTopbarComponent
        [Test/assertions]
            6
        [Test/scenario]
            :testEnv
                {Record/insert}
                    [Record/models]
                        Env
            @testEnv
            .{Record/insert}
                []
                    {Dev/comment}
                        simulate real return from RPC
                    [Record/models]
                        mail.followers
                    [mail.followers/id]
                        1
                    [mail.followers/name]
                        Jean Michang
                    [mail.followers/partner_id]
                        12
                    [mail.followers/res_id]
                        100
                    [mail.followers/res_model]
                        res.partner
                []
                    {Dev/comment}
                        simulate real return from RPC
                    [Record/models]
                        mail.followers
                    [mail.followers/id]
                        2
                    [mail.followers/name]
                        Eden Hazard
                    [mail.followers/partner_id]
                        11
                    [mail.followers/res_id]
                        100
                    [mail.followers/res_model]
                        res.partner
                []
                    [Record/models]
                        res.partner
                    [res.partner/id]
                        11
                []
                    [Record/models]
                        res.partner
                    [res.partner/id]
                        12
                []
                    [Record/models]
                        res.partner
                    [res.partner/id]
                        100
                    [res.partner/message_follower_ids]
                        1
                        2
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
                    .{Chatter/thread}
                    .{Thread/followerListMenuComponents}
                    .{Collection/length}
                    .{=}
                        1
                []
                    should have followers menu component
            {Test/assert}
                []
                    @chatter
                    .{Chatter/thread}
                    .{Thread/followerListMenuComponents}
                    .{Collection/first}
                    .{FollowerListMenuComponent/buttonFollowers}
                []
                    should have followers button

            @testEnv
            .{Component/afterNextRender}
                @testEnv
                .{UI/click}
                    @chatter
                    .{Chatter/thread}
                    .{Thread/followerListMenuComponents}
                    .{Collection/first}
                    .{FollowerListMenuComponent/buttonFollowers}
            {Test/assert}
                []
                    @chatter
                    .{Chatter/thread}
                    .{Thread/followerListMenuComponents}
                    .{Collection/first}
                    .{FollowerListMenuComponent/dropdown}
                []
                    followers dropdown should be opened
            {Test/assert}
                []
                    @chatter
                    .{Chatter/thread}
                    .{Thread/followers}
                    .{Collection/length}
                    .{=}
                        2
                []
                    exactly two followers should be listed
            {Test/assert}
                []
                    @chatter
                    .{Chatter/thread}
                    .{Thread/followers}
                    .{Collection/first}
                    .{Follower/name}
                    .{=}
                        Jean Michang
                []
                    first follower is 'Jean Michang'
            {Test/assert}
                []
                    @chatter
                    .{Chatter/thread}
                    .{Thread/followers}
                    .{Collection/second}
                    .{Follower/name}
                    .{=}
                        Eden Hazard
                []
                    second follower is 'Eden Hazard'
`;
