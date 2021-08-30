/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            confirmButton
        [Element/model]
            AttachmentDeleteConfirmComponent
        [web.Element/tag]
            button
        [web.Element/class]
            btn
            btn-primary
            me-2
        [web.Element/textContent]
            {Locale/text}
                Ok
        [Element/onClick]
            {AttachmentDeleteConfirmView/onClickOk}
                [0]
                    @record
                    .{AttachmentDeleteConfirmComponent/attachmentDeleteConfirmView}
                [1]
                    @ev
`;
