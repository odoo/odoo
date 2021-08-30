/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        States the attachment lists that are displaying this attachment.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            attachmentLists
        [Field/model]
            Attachment
        [Field/type]
            many
        [Field/target]
            AttachmentList
        [Field/inverse]
            AttachmentList/attachments
`;
