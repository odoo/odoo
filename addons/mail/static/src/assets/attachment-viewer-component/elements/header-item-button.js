/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            headerItemButton
        [Element/model]
            AttachmentViewerComponent
        [Record/models]
            Hoverable
        [web.Element/style]
            [web.scss/padding]
                [0]
                    0
                [1]
                    {scss/map-get}
                        {scss/$spacers}
                        3
            [web.scss/cursor]
                pointer
            {if}
                @field
                .{web.Element/isHover}
            .{then}
                [web.scss/background-color]
                    {scss/rgba}
                        {scss/$white}
                        0.1
                [web.scss/color]
                    {scss/lighten}
                        {scss/gray}
                            400
                        15%
`;
