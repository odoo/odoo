/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            name
        [Element/model]
            AttachmentViewerComponent
        [Record/models]
            AttachmentViewerComponent/headerItem
        [web.Element/style]
            [web.scss/margin]
                0
                {scss/map-get}
                    {scss/$spacers}
                    2
            [web.scss/min-width]
                0
`;
