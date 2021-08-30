/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Test
        [Test/name]
            livechat with logged visitor should show visitor banner
        [Test/feature]
            website_livechat
        [Test/model]
            DiscussComponent
        [Test/assertions]
            2
        [Test/behavior]
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
                            12
                []
                    [Record/models]
                        res.country
                    [res.country/id]
                        11
                    [res.country/code]
                        FAKE
                []
                    [Record/models]
                        res.partner
                    [res.partner/id]
                        12
                    [res.partner/name]
                        Partner Visitor
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
                    [website.visitor/partner_id]
                        12
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
                    .{Discuss/discussComponents}
                    .{Collection/first}
                    .{DiscussComponent/visitorBanner}
                []
                    should have a visitor banner
            {Test/assert}
                []
                    @testEnv
                    .{Discuss/discussComponents}
                    .{Collection/first}
                    .{DiscussComponent/visitorBanner}
                    .{VisitorBannerComponent/visitor}
                    .{web.Element/textContent}
                    .{=}
                        Partner Visitor
                []
                    should have partner name as display name of logged visitor on the visitor banner
`;
