/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            avatar
        [Element/model]
            VisitorBannerComponent
        [web.Element/tag]
            img
        [web.Element/class]
            rounded-circle
        [web.Element/src]
            @record
            .{VisitorBannerComponent/visitor}
            .{Visitor/avatarUrl}
        [web.Element/alt]
            {Locale/text}
                Avatar
        [web.Element/style]
            [web.scss/height]
                {scss/map-get}
                    {scss/$sizes}
                        100
            [web.scss/width]
                {scss/map-get}
                    {scss/$sizes}
                    100
            [web.scss/object-fit]
                cover
`;
