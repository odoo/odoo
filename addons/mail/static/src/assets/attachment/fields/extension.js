/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            extension
        [Field/model]
            Attachment
        [Field/type]
            attr
        [Field/compute]
            {if}
                @record
                .{Attachment/filename}
                .{&}
                    @record
                    .{Attachment/filename}
                    .{String/split}
                        .
                    .{Collection/pop}
            .{then}
                @record
                .{Attachment/filename}
                .{String/split}
                    .
                .{Collection/pop}
            .{else}
                {Record/empty}
`;
