/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Test
        [Test/name]
            livechat in the sidebar: existing user with country
        [Test/feature]
            im_livechat
        [Test/model]
            DiscussComponent
        [Test/assertions]
            3
        [Test/scenario]
            :testEnv
                {Record/insert}
                    [Record/models]
                        Env
            @testEnv
            .{Record/insert}
                [0]
                    [Record/models]
                        mail.channel
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
                            10
                [1]
                    [Record/models]
                        res.country
                    [res.country/code]
                        be
                    [res.country/id]
                        10
                    [res.country/name]
                        Belgium
                [2]
                    [Record/models]
                        res.partner
                    [res.partner/country_id]
                        10
                    [res.partner/id]
                        10
                    [res.partner/name]
                        Jean
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
                    .{Discuss/discussSidebarComponents}
                    .{Collection/first}
                    .{DiscussSidebarComponent/categoryLivechat}
                []
                    should have a channel category livechat in the side bar
            {Test/assert}
                []
                    @testEnv
                    .{Discuss/discussSidebarComponents}
                    .{Collection/first}
                    .{DiscussSidebarComponent/categoryLivechat}
                    .{DiscussSidebarCategoryComponent/item}
                    .{Collection/length}
                    .{=}
                        1
                []
                    should have a livechat in sidebar
            {Test/assert}
                []
                    @testEnv
                    .{Discuss/discussSidebarComponents}
                    .{Collection/first}
                    .{DiscussSidebarComponent/categoryLivechat}
                    .{DiscussSidebarCategoryComponent/item}
                    .{Collection/first}
                    .{web.Element/textContent}
                    .{=}
                        Jean (Belgium)
                []
                    should have user name and country as livechat name
`;
