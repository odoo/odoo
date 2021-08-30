/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            attachment
        [Field/model]
            AttachmentViewer
        [Field/type]
            one
        [Field/target]
            Attachment
        [Field/related]
            AttachmentViewer/attachmentList
            AttachmentList/selectedAttachment
`;
