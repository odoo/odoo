/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            isViewable
        [Field/model]
            Attachment
        [Field/type]
            attr
        [Field/target]
            Boolean
        [Field/compute]
            @record
            .{Attachment/isText}
            .{|}
                @record
                .{Attachment/isImage}
            .{|}
                @record
                .{Attachment/isVideo}
            .{|}
                @record
                .{Attachment/isPdf}
            .{|}
                @record
                .{Attachmemt/isUrlYoutube}
`;
