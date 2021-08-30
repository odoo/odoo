/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Link with a message view to handle attachments.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            messageViewOwner
        [Field/model]
            AttachmentList
        [Field/type]
            one
        [Field/target]
            MessageView
        [Field/isReadonly]
            true
        [Field/inverse]
            MessageView/attachmentList
`;
