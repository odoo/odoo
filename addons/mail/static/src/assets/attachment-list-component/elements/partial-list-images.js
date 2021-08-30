/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            partialListImages
        [Element/model]
            AttachmentListComponent
        [Record/models]
            AttachmentListComponent/partialList
`;
