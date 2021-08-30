/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Abort Controller linked to the uploading process of this attachment.
        Useful in order to cancel the in-progress uploading of this attachment.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            uploadingAbortController
        [Field/model]
            Attachment
        [Field/type]
            attr
        [Field/compute]
            {if}
                @record
                .{Attachment/isUploading}
            .{then}
                {if}
                    @record
                    .{Attachment/uploadingAbortController}
                    .{isFalsy}
                .{then}
                    {Record/insert}
                        [Record/models]
                            AbortController
                        [AbortController/onSignalAbort]
                            {Env/messagingBus}
                            .{Bus/trigger}
                                [0]
                                    o-attachment-upload-abort
                                [1]
                                    [record]
                                        @record
                .{else}
                    @record
                    .{Attachment/uploadingAbortController}
            .{else}
                {Record/empty}
`;
