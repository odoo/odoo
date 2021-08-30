/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        States if the attachment is a video.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            isVideo
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
                audio/mpeg
                video/x-matroska
                video/mp4
                video/webm
            .{Collection/includes}
                @record
                .{Attachment/mimetype}
`;
