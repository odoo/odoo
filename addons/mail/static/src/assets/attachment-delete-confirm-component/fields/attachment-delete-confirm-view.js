/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            attachmentDeleteConfirmView
        [Field/model]
            AttachmentDeleteConfirmComponent
        [Field/type]
            one
        [Field/target]
            AttachmentDeleteConfirmView
        [Field/isRequired]
            true
        [Field/inverse]
            AttachmentDeleteConfirmView/component
`;
