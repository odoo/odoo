/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        This field determines whether some attachments linked to this
        composer are being uploaded.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            hasUploadingAttachment
        [Field/model]
            Composer
        [Field/type]
            attr
        [Field/target]
            Boolean
        [Field/compute]
            @record
            .{Composer/attachments}
            .{Collection/some}
                [Attachment/isUploading]
                    true
`;
