/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Model
        [Model/name]
            AttachmentBoxView
        [Model/fields]
            attachmentList
            chatter
            component
            fileUploader
        [Model/id]
            AttachmentBoxView/chatter
        [Model/actions]
            AttachmentBoxView/onClickAddAttachment
`;
