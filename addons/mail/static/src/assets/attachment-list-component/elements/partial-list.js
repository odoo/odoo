/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            partialList
        [Element/model]
            AttachmentListComponent
        [web.Element/class]
            d-flex
            flex-grow-1
            flex-wrap
`;
