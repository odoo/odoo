/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            command
        [Element/model]
            ChatWindowHeaderComponent
        [Record/models]
            Hoverable
        [web.Element/style]
            [web.scss/padding]
                [0]
                    {scss/map-get}
                        {scss/$spacers}
                        0
                [1]
                    {scss/map-get}
                        {scss/$spacers}
                        3
            [web.scss/display]
                flex
            [web.scss/height]
                {scss/map-get}
                    {scss/$sizes}
                    100
            [web.scss/align-items]
                center
            [web.scss/cursor]
                pointer
            {if}
                @field
                .{web.Element/isHover}
            .{then}
                [web.scss/background-color]
                    {scss/rgba}
                        {scss/$black}
                        0.1
            {if}
                {Device/isMobile}
            .{then}
                [web.scss/font-size]
                    1.3
                    rem
`;
