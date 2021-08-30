/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            partialListNonImages
        [Element/model]
            AttachmentListComponent
        [Record/models]
            AttachmentListComponent/partialList
        [web.Element/class]
            justify-content-start
            m-1
`;
