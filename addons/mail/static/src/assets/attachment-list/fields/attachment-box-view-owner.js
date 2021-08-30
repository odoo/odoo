/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Link with a AttachmentBoxView to handle attachments.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            attachmentBoxViewOwner
        [Field/model]
            AttachmentList
        [Field/type]
            one
        [Field/target]
            AttachmentBoxView
        [Field/isReadonly]
            true
        [Field/inverse]
            Chatter/attachmentList
`;
