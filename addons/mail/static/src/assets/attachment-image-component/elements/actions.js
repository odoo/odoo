/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            actions
        [Element/model]
            AttachmentImageComponent
        [web.Element/class]
            d-flex
            flex-column
            justify-content-between
`;
