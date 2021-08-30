/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Model
        [Model/name]
            FileUploader
        [Model/fields]
            activityView
            attachmentBoxView
            composerView
            fileInput
            thread
        [Model/id]
            FileUploader/activityView
            .{|}
                FileUploader/attachmentBoxView
            .{|}
                FileUploader/composerView
        [Model/actions]
            FileUploader/_createFormData
            FileUploader/_onAttachmentUploaded
            FileUploader/_performUpload
            FileUploader/getAttachmentNextTemporaryId
            FileUploader/onChangeAttachment
            FileUploader/openBrowserFileUploader
            FileUploader/uploadFiles
`;
