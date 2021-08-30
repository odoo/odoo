/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Handles click on the "add attachment" button.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            AttachmentBoxView/onClickAddAttachment
        [Action/params]
            record
                [type]
                    AttachmentBoxView
        [Action/behavior]
            {FileUploader/openBrowserFileUploader}
                @record
                .{AttachmentBoxView/fileUploader}
`;
