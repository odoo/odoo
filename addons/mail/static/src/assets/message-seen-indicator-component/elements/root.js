/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            root
        [Element/model]
            MessageSeenIndicatorComponent
        [web.Element/tag]
            span
        [Record/models]
            Hoverable
        [web.Element/title]
            @record
            .{MessageSeenIndicatorComponent/messageSeenIndicator}
            .{MessageSeenIndicator/title}
        [web.Element/style]
            [web.scss/display]
                flex
            [web.scss/position]
                relative
            [web.scss/flex-wrap]
                nowrap
            [web.scss/opacity]
                0.6
            {if}
                @record
                .{MessageSeenIndicatorComponent/messageSeenIndicator}
                .{MessageSeenIndicator/hasEveryoneSeen}
            .{then}
                [web.scss/color]
                    {scss/$o-brand-odoo}
            {if}
                @field
                .{web.Element/isHover}
            .{then}
                [web.scss/cursor]
                    pointer
                [web.scss/opacity]
                    0.8
`;
