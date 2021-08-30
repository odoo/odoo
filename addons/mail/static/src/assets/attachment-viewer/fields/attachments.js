/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            attachments
        [Field/model]
            AttachmentViewer
        [Field/type]
            many
        [Field/target]
            Attachment
        [Field/related]
            AttachmentViewer/attachmentList
            AttachmentList/viewableAttachments
`;
