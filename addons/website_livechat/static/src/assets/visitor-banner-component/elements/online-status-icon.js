/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            onlineStatusIcon
        [Element/model]
            VisitorBannerComponent
        [web.Element/tag]
            i
        [web.Element/class]
            fa
            fa-circle
        [Element/isPresent]
            @record
            .{VisitorBannerComponent/visitor}
            .{Visitor/isConnected}
        [web.Element/title]
            {Locale/text}
                Online
        [web.Element/role]
            img
        [web.Element/aria-label]
            {Locale/text}
                Visitor is online
        [web.Element/style]
            {web.scss/include}
                {web.scss/o-position-absolute}
                    [$bottom]
                        0
                    [$right]
                        0
            [web.scss/display]
                flex
            [web.scss/align-items]
                center
            [web.scss/justify-content]
                center
            [web.scss/flex-flow]
                column
            [web.scss/width]
                1.2em
            [web.scss/height]
                1.2em
            [web.scss/line-height]
                1.3em
            [web.scss/font-size]
                x-small
            [web.scss/color]
                {scss/$o-enterprise-primary-color}
`;
