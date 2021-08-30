/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Context
        [Context/name]
            imageAttachment
        [Context/model]
            AttachmentListComponent
        [Model/fields]
            attachmentImage
        [Model/template]
            attachmentImageForeach
                attachmentImage
`;
