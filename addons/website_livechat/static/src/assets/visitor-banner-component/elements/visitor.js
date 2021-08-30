/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            visitor
        [Element/model]
            VisitorBannerComponent
        [web.Element/tag]
            span
        [web.Element/textContent]
            @record
            .{VisitorBannerComponent/visitor}
            .{Visitor/nameOrDisplayName}
        [web.Element/style]
            [web.scss/margin-inline-end]
                {scss/map-get}
                    {scss/$spacers}
                    3
            [web.scss/font-weight]
                {scss/$font-weight-bold}
`;
