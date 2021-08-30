/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Model
        [Model/name]
            AttachmentDeleteConfirmView
        [Model/fields]
            AttachmentDeleteConfirmView/dialogOwner
        [Model/id]
        [Model/actions]
            AttachmentDeleteConfirmView/containsElement
            AttachmentDeleteConfirmView/onClickCancel
            AttachmentDeleteConfirmView/onClickOk
`;
