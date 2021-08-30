/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Test
        [Test/name]
            hover following button
        [Test/model]
            FollowButtonComponent
        [Test/assertions]
            8
        [Test/scenario]
            :testEnv
                {Record/insert}
                    [Record/models]
                        Env
            @testEnv
            .{Record/insert}
                []
                    [Record/models]
                        mail.followers
                    [mail.followers/id]
                        1
                    [mail.followers/is_active]
                        true
                    [mail.followers/is_editable]
                        true
                    [mail.followers/partner_id]
                        @record
                        .{Test/data}
                        .{Data/currentPartnerId}
                    [mail.followers/res_id]
                        100
                    [mail.followers/res_model]
                        res.partner
                []
                    [Record/models]
                        res.partner
                    [res.partner/id]
                        100
                    [res.partner/message_follower_ids]
                        1
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
            .{Thread/follow}
                @thread
            @testEnv
            .{Record/insert}
                [Record/models]
                    FollowButtonComponent
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
                    .{FollowButtonComponent/unfollow}
                []
                    should have 'Unfollow' button
            {Test/assert}
                []
                    @thread
                    .{Thread/followButtonComponents}
                    .{Collection/first}
                    .{FollowButtonComponent/unfollow}
                    .{web.Element/textContent}
                    .{=}
                        Following
                []
                    unfollow' button should display 'Following' as text when not hovered
            {Test/assert}
                []
                    @thread
                    .{Thread/followButtonComponents}
                    .{Collection/first}
                    .{web.Element/unfollowIcon}
                    .{isFalsy}
                []
                    'unfollow' button should not contain a cross icon when not hovered
            {Test/assert}
                []
                    @thread
                    .{Thread/followButtonComponents}
                    .{Collection/first}
                    .{FollowButtonComponent/followingIcon}
                []
                    'unfollow' button should contain a check icon when not hovered

            @testEnv
            .{Component/afterNextRender}
                @testEnv
                .{UI/mouseenter}
                    @thread
                    .{Thread/followButtonComponents}
                    .{Collection/first}
                    .{FollowButtonComponent/unfollow}
            {Test/assert}
                []
                    @thread
                    .{Thread/followButtonComponents}
                    .{Collection/first}
                    .{FollowButtonComponent/unfollow}
                    .{web.Element/textContent}
                    .{=}
                        Unfollow
                []
                    'unfollow' button should display 'Unfollow' as text when hovered
            {Test/assert}
                []
                    @thread
                    .{Thread/followButtonComponents}
                    .{Collection/first}
                    .{FollowButtonComponent/unfollowIcon}
                []
                    'unfollow' button should contain a cross icon when hovered
            {Test/assert}
                []
                    @thread
                    .{Thread/followButtonComponents}
                    .{Collection/first}
                    .{FollowButtonComponent/followingIcon}
                    .{isFalsy}
                []
                    'unfollow' button should not contain a check icon when hovered
`;
