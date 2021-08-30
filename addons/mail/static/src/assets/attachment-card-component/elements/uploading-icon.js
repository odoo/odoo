/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            uploadingIcon
        [Element/model]
            AttachmentCardComponent
        [web.Element/tag]
            i
        [web.Element/class]
            fa
            fa-spin
            fa-spinner
`;
