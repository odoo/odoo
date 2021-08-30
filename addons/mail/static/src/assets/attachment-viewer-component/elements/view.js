/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            view
        [Element/model]
            AttachmentViewerComponent
        [web.Element/style]
            [web.scss/background-color]
                {scss/$black}
            [web.scss/box-shadow]
                0
                0
                40px
                {scss/$black}
            [web.scss/outline]
                none
            [web.scss/border]
                none
`;
