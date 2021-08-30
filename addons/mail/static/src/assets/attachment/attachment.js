/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Model
        [Model/name]
            Attachment
        [Model/fields]
            accessToken
            activities
            attachmentLists
            checksum
            composer
            defaultSource
            dialogRef
            displayName
            downloadUrl
            extension
            filename
            id
            isEditable
            isImage
            isMain
            isPdf
            isText
            isUnlinkPending
            isUploading
            isUrl
            isUrlYoutube
            isVideo
            isViewable
            messages
            mimetype
            name
            originThread
            size
            threads
            type
            uploadingAbortController
            url
        [Model/id]
            Attachment/id
        [Model/actions]
            Attachment/convertData
            Attachment/download
            Attachment/onClickDownload
            Attachment/remove
`;
