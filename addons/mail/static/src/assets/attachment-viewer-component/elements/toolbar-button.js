/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            toolbarButton
        [Element/model]
            AttachmentViewerComponent
        [web.Element/style]
            [web.scss/padding]
                8
                px
            [web.scss/background-color]
                {scss/lighten}
                    {scss/$black}
                    15%
`;
