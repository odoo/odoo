/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            label
        [Element/model]
            FollowerSubtypeComponent
        [web.Element/tag]
            label
        [Record/models]
            Hoverable
        [web.Element/style]
            [web.scss/display]
                flex
            [web.scss/flex]
                1
            [web.scss/flex-direction]
                row
            [web.scss/align-items]
                center
            [web.scss/margin-bottom]
                {scss/map-get}
                    {scss/$spacers}
                    0
            [web.scss/padding]
                {scss/map-get}
                    {scss/$spacers}
                    2
            [web.scss/cursor]
                pointer
            {if}
                @field
                .{web.Element/isHover}
            .{then}
                [web.scss/background-color]
                    {scss/gray}
                        200
`;
