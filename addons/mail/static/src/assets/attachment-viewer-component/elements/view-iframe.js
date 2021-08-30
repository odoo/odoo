/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            viewIframe
        [Element/model]
            AttachmentViewerComponent
        [web.Element/style]
            [web.scss/width]
                90%
            [web.scss/height]
                100%
            {if}
                {Device/isMobile}
            .{then}
                [web.scss/width]
                    {scss/map-get}
                        {scss/$sizes}
                        100
`;
