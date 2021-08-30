/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            visitorBanner
        [Element/feature]
            website_livechat
        [Element/model]
            DiscussComponent
        [Field/target]
            VisitorBannerComponent
        [Element/isPresent]
            @record
            .{DiscussComponent/discussView}
            .{DiscussView/discuss}
            .{Discuss/thread}
            .{Thread/visitor}
        [VisitorBannerComponent/visitor]
            @record
            .{DiscussComponent/discussView}
            .{Discuss/discussView}
            .{Discuss/thread}
            .{Thread/visitor}
`;
