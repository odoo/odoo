/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Test
        [Test/name]
            livechat - states: the active category item should be visble even if the category is closed
        [Test/model]
            DiscussSidebarCategoryComponent
        [Test/feature]
            im_livechat
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
                    mail.channel
                [mail.channel/anonymous_name]
                    Visitor 11
                [mail.channel/channel_type]
                    livechat
                [mail.channel/id]
                    11
                [mail.channel/livechat_operator_id]
                    @record
                    .{Test/data}
                    .{Data/currentPartnerId}
                [mail.channel/members]
                    [0]
                        @record
                        .{Test/data}
                        .{Data/currentPartnerId}
                    [1]
                        @record
                        .{Test/data}
                        .{Data/publicPartnerId}
            @testEnv
            .{Record/insert}
                [Record/models]
                    Server
                [Server/data]
                    @record
                    .{Test/data}
            {Test/assert}
                @testEnv
                .{Record/findById}
                    [Thread/id]
                        11
                    [Thread/model]
                        mail.channel
                .{Thread/discussSidebarCategoryItemComponents}
                .{Collection/length}
                .{=}
                    1

            :livechat
                @testEnv
                .{Record/findById}
                    [Thread/id]
                        11
                    [Thread/model]
                        mail.channel
                .{Thread/discussSidebarCategoryItemComponents}
                .{Collection/first}
            @testEnv
            .{UI/afterNextRender}
                @testEnv
                .{UI/click}
                    @livechat
            {Test/assert}
                @livechat
                .{DicussSidebarCategoryComponent/isActive}

            @testEnv
            .{UI/afterNextRender}
                @testEnv
                .{UI/click}
                    @testEnv
                    .{Discuss/categoryLivechat}
                    .{DiscussSidebarCategory/discussSidebarCategoryComponents}
                    .{Collection/first}
                    .{DiscussSidebarCategoryComponent/title}
            {Test/assert}
                []
                    @testEnv
                    .{Record/findById}
                        [Thread/id]
                            11
                        [Thread/model]
                            mail.channel
                    .{Thread/discussSidebarCategoryItemComponents}
                    .{Collection/length}
                    .{=}
                        1
                []
                    the active livechat item should remain even if the category is folded
`;
