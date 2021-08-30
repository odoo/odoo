/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            buttonNavigation
        [Element/model]
            AttachmentViewerComponent
        [Record/models]
            Hoverable
        [web.Element/style]
            [web.scss/position]
                absolute
            [web.scss/display]
                flex
            [web.scss/align-items]
                center
            [web.scss/justify-content]
                center
            [web.scss/width]
                40
                px
            [web.scss/height]
                40
                px
            [web.scss/top]
                50%
            [web.scss/transform]
                {web.scss/translateY}
                    -50%
            [web.scss/color]
                {scss/gray}
                    400
            [web.scss/background-color]
                {scss/lighten}
                    {scss/$black}
                    15%
            [web.scss/border-radius]
                100%
            [web.scss/cursor]
                pointer
            {if}
                @field
                .{web.Element/isHover}
            .{then}
                [web.scss/color]
                    {scss/lighten}
                        {scss/gray}
                            400
                        15%
                [web.scss/background-color]
                    {scss/$black}
`;
