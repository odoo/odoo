/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            mainText
        [Element/model]
            AttachmentDeleteConfirmComponent
        [web.Element/tag]
            p
        [web.Element/class]
            mx-3
            mb-3
        [web.Element/textContent]
            @record
            .{AttachmentDeleteConfirmComponent/attachmentDeleteConfirmView}
            .{AttachmentDeleteConfirmView/body}
`;
