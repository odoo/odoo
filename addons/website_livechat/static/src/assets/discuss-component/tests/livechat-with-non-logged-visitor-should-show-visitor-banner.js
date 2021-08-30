/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Test
        [Test/name]
            livechat with non-logged visitor should show visitor banner
        [Test/feature]
            website_livechat
        [Test/model]
            DiscussComponent
        [Test/assertions]
            1
        [Test/scenario]
            :testEnv
                {Record/insert}
                    [Record/models]
                        Env
            @testEnv
            .{Record/insert}
                []
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
                    [mail.channel/livechat_visitor_id]
                        11
                    [mail.channel/members]
                        [0]
                            @record
                            .{Test/data}
                            .{Data/currentPartnerId}
                        [1]
                            @record
                            .{Test/data}
                            .{Data/publicPartnerId}
                []
                    [Record/models]
                        res.country
                    [res.country/id]
                        11
                    [res.country/code]
                        FAKE
                []
                    [Record/models]
                        website.visitor
                    [website.visitor/id]
                        11
                    [website.visitor/country_id]
                        11
                    [website.visitor/display_name]
                        Visitor #11
                    [website.visitor/history]
                        Home → Contact
                    [website.visitor/is_connected]
                        true
                    [website.visitor/lang_name]
                        English
                    [website.visitor/website_name]
                        General website
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
            @testEnv
            .{Thread/open}
                @testEnv
                .{Record/findById}
                    [Thread/id]
                        11
                    [Thread/model]
                        mail.channel
            {Test/assert}
                []
                    @testEnv
                    .{Record/all}
                        [Record/models]
                            VisitorBannerComponent
                    .{Collection/length}
                    .{=}
                        1
                []
                    should have a visitor banner
`;
