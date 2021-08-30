/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            unlinkIcon
        [Element/model]
            AttachmentImageComponent
        [web.Element/tag]
            i
        [web.Element/class]
            fa
            fa-trash
`;
