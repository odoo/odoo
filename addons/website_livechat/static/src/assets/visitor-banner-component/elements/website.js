/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            website
        [Element/model]
            VisitorBannerComponent
        [web.Element/tag]
            span
        [Element/isPresent]
            @record
            .{VisitorBannerComponent/visitor}
            .{Visitor/websiteName}
`;
