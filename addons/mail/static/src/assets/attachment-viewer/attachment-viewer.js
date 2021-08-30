/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Model
        [Model/name]
            AttachmentViewer
        [Model/fields]
            angle
            attachment
            attachmentList
            attachments
            component
            dialogOwner
            imageUrl
            isDragging
            isImageLoading
            scale
        [Model/id]
            AttachmentViewer/dialogOwner
        [Model/actions]
            AttachmentViewer/containsElement
`;
