/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            toolbarButtonDownloadIcon
        [Element/model]
            AttachmentViewerComponent
        [web.Element/tag]
            i
        [web.Element/class]
            fa
            fa-download
            fa-fw
        [web.Element/role]
            img
`;
