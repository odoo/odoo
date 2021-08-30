/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        States if the attachment is an image.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            isImage
        [Field/model]
            Attachment
        [Field/type]
            attr
        [Field/target]
            Boolean
        [Field/compute]
            {Record/insert}
                [Record/models]
                    Collection
                image/bmp
                image/gif
                image/jpeg
                image/png
                image/svg+xml
                image/tiff
                image/x-icon
            .{Collection/includes}
                @record
                .{Attachment/mimetype}
`;
