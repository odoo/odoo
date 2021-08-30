/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determines if the attachment is a youtube url.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            isUrlYoutube
        [Field/model]
            Attachment
        [Field/type]
            attr
        [Field/target]
            Boolean
        [Field/compute]
            @record
            .{Attachment/url}
            .{isTruthy}
            .{&}
                @record
                .{Attachment/url}
                .{String/includes}
                    youtu
`;
