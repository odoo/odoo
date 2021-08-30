/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            allAttachments
        [Field/model]
            Thread
        [Field/type]
            many
        [Field/target]
            Attachment
        [Field/compute]
            @record
            .{Thread/originThreadAttachments}
            .{Collection/concat}
                @record
                .{Thread/attachments}
            .{Collection/unique}
            .{Collection/sort}
                {Record/insert}
                    [Record/models]
                        Function
                    [Function/in]
                        item1
                        item2
                    [Function/out]
                        {Dev/comment}
                            "uploading" before "uploaded" attachments.
                        {if}
                            @item1
                            .{Attachment/isUploading}
                            .{isFalsy}
                            .{&}
                                @item2
                                .{Attachment/isUploading}
                        .{then}
                            1
                        .{elif}
                            @item1
                            .{Attachment/isUploading}
                            .{&}
                                @item2
                                .{Attachment/isUploading}
                                .{isFalsy}
                        .{then}
                            -1
                        .{else}
                            {Dev/comment}
                                "most-recent" before "oldest" attachments.
                            {Math/abs}
                                @item2
                                .{Attachment/id}
                            .{-}
                                {Math/abs}
                                    @item1
                                    .{Attachment/id}
`;
