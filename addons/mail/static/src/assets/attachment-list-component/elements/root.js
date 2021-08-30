/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            root
        [Element/model]
            AttachmentListComponent
        [web.Element/class]
            d-flex
            flex-column
            justify-content-start
`;
