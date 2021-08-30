/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            attachmentBoxView
        [Field/model]
            FileUploader
        [Field/type]
            one
        [Field/target]
            AttachmentBoxView
        [Field/isReadonly]
            true
        [Field/inverse]
            AttachmentBoxView/fileUploader
`;
