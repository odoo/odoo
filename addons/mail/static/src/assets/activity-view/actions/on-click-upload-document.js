/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Handles the click on the upload document button. This open the file
        explorer for upload.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            ActivityView/onClickUploadDocument
        [Action/params]
            record
                [type]
                    ActivityView
        [Action/behavior]
            {FileUploader/openBrowserFileUploader}
                @record
                .{ActivityView/fileUploader}
`;
