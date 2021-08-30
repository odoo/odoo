/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            content
        [Element/model]
            AttachmentBoxComponent
        [web.Element/class]
            d-flex
            flex-column
`;
