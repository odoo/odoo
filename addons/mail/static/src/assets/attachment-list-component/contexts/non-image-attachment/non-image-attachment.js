/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Context
        [Context/name]
            nonImageAttachment
        [Context/model]
            AttachmentListComponent
        [Model/fields]
            attachmentCard
        [Model/template]
            nonImageAttachmentForeach
                nonImageAttachment
`;
