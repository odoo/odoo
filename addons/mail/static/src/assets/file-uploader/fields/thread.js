/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            thread
        [Field/model]
            FileUploader
        [Field/type]
            one
        [Field/target]
            Thread
        [Field/isRequired]
            true
        [Field/isReadonly]
            true
        [Field/compute]
            {if}
                @record
                .{FileUploader/activityView}
            .{then}
                @record
                .{FileUploader/activityView}
                .{ActivityView/activity}
                .{Activity/thread}
            .{elif}
                @record
                .{FileUploader/attachmentBoxView}
            .{then}
                @record
                .{FileUploader/attachmentBoxView}
                .{AttachmentBoxView/chatter}
                .{Chatter/thread}
            .{elif}
                @record
                .{FileUploader/composerView}
            .{then}
                @record
                .{FileUploader/composerView}
                .{ComposerView/composer}
                .{Composer/activeThread}
            .{else}
                {Record/empty}
`;
