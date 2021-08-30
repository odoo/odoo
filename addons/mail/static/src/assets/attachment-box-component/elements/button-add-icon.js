/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            buttonAddIcon
        [Element/model]
            AttachmentBoxComponent
        [web.Element/tag]
            i
        [web.Element/class]
            fa
            fa-plus-square
`;
