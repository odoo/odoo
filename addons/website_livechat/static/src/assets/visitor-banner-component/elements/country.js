/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            country
        [Element/model]
            VisitorBannerComponent
        [web.Element/tag]
            img
        [web.Element/class]
            o_country_flag
        [Element/isPresent]
            @record
            .{VisitorBannerComponent/visitor}
            .{Visitor/country}
        [web.Element/src]
            @record
            .{VisitorBannerComponent/visitor}
            .{Visitor/country}
            .{Country/flagUrl}
        [web.Element/alt]
            @record
            .{VisitorBannerComponent/visitor}
            .{Visitor/country}
            .{Country/code}
            .{|}
                @record
                .{VisitorBannerComponent/visitor}
                .{Visitor/country}
                .{Country/name}
        [web.Element/style]
            [web.scss/margin-inline-end]
                {scss/map-get}
                    {scss/$spacers}
                    1
`;
