/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Model
        [Model/name]
            AttachmentCard
        [Model/fields]
            attachment
            attachmentDeleteConfirmDialog
            attachmentList
            component
        [Model/id]
            AttachmentCard/attachmentList
            .{&}
                AttachmentCard/attachment
        [Model/actions]
            AttachmentCard/onClickImage
            AttachmentCard/onClickUnlink
`;
