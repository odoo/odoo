/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Test
        [Test/name]
            channel - command: should not have add command when category is folded
        [Test/model]
            DiscussSidebarCategoryComponent
        [Test/assertions]
            1
        [Test/scenario]
            :testEnv
                {Record/insert}
                    [Record/models]
                        Env
            @testEnv
            .{Record/insert}
                [Record/models]
                    res.users.settings
                [res.users.settings/user_id]
                    @record
                    .{Test/data}
                    .{Data/currentUserId}
                [res.users.settings/is_discuss_sidebar_category_channel_open]
                    false
            @testEnv
            .{Record/insert}
                [Record/models]
                    Server
                [Server/data]
                    @record
                    .{Test/data}
            {Test/assert}
                []
                    @testEnv
                    .{Discuss/categoryChannel}
                    .{DiscussSidebarCategory/hasAddCommand}
                    .{isFalsy}
                []
                    should not have add command when channel category is closed
`;
