/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            cancelButton
        [Element/model]
            AttachmentDeleteConfirmComponent
        [web.Element/tag]
            button
        [web.Element/class]
            btn
            btn-secondary
        [web.Element/textContent]
            {Locale/text}
                Cancel
        [Element/onClick]
            {AttachmentDeleteConfirmView/onClickCancel}
                [0]
                    @record
                    .{AttachmentDeleteConfirmComponent/attachmentDeleteConfirmView}
                [1]
                    @ev
`;
