/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Post a message in the composer on related thread.

        Posting of the message could be aborted if it cannot be posted like if there are attachments
        currently uploading or if there is no text content and no attachments.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            ComposerViewComponent/_postMessage
        [Action/params]
            record
                [type]
                    ComposerViewComponent
        [Action/behavior]
            {if}
                @record
                .{ComposerViewComponent/composerView}
                .{ComposerView/composer}
                .{Composer/canPostMessage}
                .{isFalsy}
            .{then}
                {if}
                    @record
                    .{ComposerViewComponent/composerView}
                    .{ComposerView/composer}
                    .{Composer/hasUploadingAttachment}
                .{then}
                    @env
                    .{Env/owlEnv}
                    .{Dict/get}
                        services
                    .{Dict/get}
                        notification
                    .{Dict/get}
                        notify
                    .{Function/call}
                        [message]
                            {Locale/text}
                                Please wait while the file is uploading.
                        [type]
                            warning
                {break}
            {if}
                @record
                .{ComposerViewComponent/composerView}
                .{ComposerView/messageViewInEditing}
            .{then}
                {ComposerView/updateMessage}
                    @record
                    .{ComposerViewComponent/composerView}
                {break}
            {ComposerView/postMessage}
                @record
                .{ComposerViewComponent/composerView}
`;
