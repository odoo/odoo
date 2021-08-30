/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            headerItem
        [Element/model]
            AttachmentViewerComponent
        [web.Element/style]
            [web.scss/display]
                flex
            [web.scss/align-items]
                center
`;
