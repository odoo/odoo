/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Test
        [Test/name]
            chat - avatar: should have correct avatar
        [Test/model]
            DiscussSidebarCategoryItemComponent
        [Test/assertions]
            2
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
                        chat
                    [mail.channel/id]
                        10
                    [mail.channel/members]
                        [0]
                            @record
                            .{Test/data}
                            .{Data/currentPartnerId}
                        [1]
                            15
                    [mail.channel/public]
                        private
                [1]
                    [Record/models]
                        res.partner
                    [res.partner/id]
                        15
                    [res.partner/name]
                        Demo
                    [res.partner/im_status]
                        offline
            @testEnv
            .{Record/insert}
                [Record/models]
                    Server
                [Server/data]
                    @record
                    .{Test/data}
            :chatItem
                @testEnv
                .{Record/findById}
                    [Thread/id]
                        10
                    [Thread/model]
                        mail.channel
                .{Thread/discussSidebarCategoryItemComponents}
                .{Collection/first}
            {Test/assert}
                []
                    @chatItem
                    .{DiscussSidebarCategoryItemComponent/image}
                []
                    chat should have an avatar
            {Test/assert}
                []
                    @chatItem
                    .{DiscussSidebarCategoryItemComponent/image}
                    .{web.Element/src}
                    .{=}
                        /web/image/res.partner/15/avatar_128
                []
                    should link to the partner avatar
`;
