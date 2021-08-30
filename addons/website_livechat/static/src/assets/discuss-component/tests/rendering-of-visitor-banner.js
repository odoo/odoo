/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Test
        [Test/name]
            rendering of visitor banner
        [Test/feature]
            website_livechat
        [Test/model]
            DiscussComponent
        [Test/assertions]
            13
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
                    [res.country/code]
                        FAKE
                    [res.country/id]
                        11
                []
                    [Record/models]
                        website.visitor
                    [website.visitor/country_id]
                        11
                    [website.visitor/display_name]
                        Visitor #11
                    [website.visitor/history]
                        Home → Contact
                    [website.visitor/id]
                        11
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
                    .{VisitorBannerComponent/avatar}
                []
                    should show the visitor avatar in the banner
            {Test/assert}
                []
                    @testEnv
                    .{Discuss/discussComponents}
                    .{Collection/first}
                    .{DiscussComponent/visitorBanner}
                    .{VisitorBannerComponent/avatar}
                    .{web.Element/src}
                    .{=}
                        /mail/static/src/img/smiley/avatar.jpg
                []
                    should show the default avatar
            {Test/assert}
                []
                    @testEnv
                    .{Discuss/discussComponents}
                    .{Collection/first}
                    .{DiscussComponent/visitorBanner}
                    .{VisitorBannerComponent/onlineStatusIcon}
                []
                    should show the visitor online status icon on the avatar
            {Test/assert}
                []
                    @testEnv
                    .{Discuss/discussComponents}
                    .{Collection/first}
                    .{DiscussComponent/visitorBanner}
                    .{VisitorBannerComponent/country}
                    .{web.Element/src}
                    .{=}
                        /base/static/img/country_flags/FAKE.png
                []
                    should show the flag of the country of the visitor
            {Test/assert}
                []
                    @testEnv
                    .{Discuss/discussComponents}
                    .{Collection/first}
                    .{DiscussComponent/visitorBanner}
                    .{VisitorBannerComponent/visitor}
                []
                    should show the visitor name in the banner
            {Test/assert}
                []
                    @testEnv
                    .{Discuss/discussComponents}
                    .{Collection/first}
                    .{DiscussComponent/visitorBanner}
                    .{VisitorBannerComponent/visitor}
                    .{web.Element/textContent}
                    .{=}
                        Visitor #11
                []
                    should have 'Visitor #11' as visitor name
            {Test/assert}
                []
                    @testEnv
                    .{Discuss/discussComponents}
                    .{Collection/first}
                    .{DiscussComponent/visitorBanner}
                    .{VisitorBannerComponent/language}
                []
                    should show the visitor language in the banner
            {Test/assert}
                []
                    @testEnv
                    .{Discuss/discussComponents}
                    .{Collection/first}
                    .{DiscussComponent/visitorBanner}
                    .{VisitorBannerComponent/language}
                    .{web.Element/textContent}
                    .{=}
                        English
                []
                    should have 'English' as language of the visitor
            {Test/assert}
                []
                    @testEnv
                    .{Discuss/discussComponents}
                    .{Collection/first}
                    .{DiscussComponent/visitorBanner}
                    .{VisitorBannerComponent/website}
                []
                    should show the visitor website in the banner
            {Test/assert}
                []
                    @testEnv
                    .{Discuss/discussComponents}
                    .{Collection/first}
                    .{DiscussComponent/visitorBanner}
                    .{VisitorBannerComponent/website}
                    .{web.Element/textContent}
                    .{=}
                        General website
                []
                    should have 'General website' as website of the visitor
            {Test/assert}
                []
                    @testEnv
                    .{Discuss/discussComponents}
                    .{Collection/first}
                    .{DiscussComponent/visitorBanner}
                    .{VisitorBannerComponent/history}
                []
                    should show the visitor history in the banner
            {Test/assert}
                []
                    @testEnv
                    .{Discuss/discussComponents}
                    .{Collection/first}
                    .{DiscussComponent/visitorBanner}
                    .{VisitorBannerComponent/history}
                    .{web.Element/textContent}
                    .{=}
                        Home → Contact
                []
                    should have 'Home → Contact' as history of the visitor
`;
