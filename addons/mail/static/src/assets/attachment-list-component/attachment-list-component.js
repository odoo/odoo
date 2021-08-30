/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Model
        [Model/name]
            AttachmentListComponent
        [Model/fields]
            attachmentList
        [Model/template]
            root
                partialListImages
                    imageAttachmentForeach
                partialListNonImages
                    nonImageAttachmentForeach
        [Model/actions]
            AttachmentListComponent/imageAttachments
            AttachmentListComponent/nonImageAttachments
            AttachmentListComponent/viewableAttachments
`;
