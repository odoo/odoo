/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Handles click on the save link.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            ComposerView/onClickSaveLink
        [Action/params]
            record
                [type]
                    ComposerView
            ev
                [type]
                    MouseEvent
        [Action/behavior]
            {web.Event/preventDefaut}
                @ev
            {if}
                @record
                .{ComposerView/composer}
                .{Composer/canPostMessage}
                .{isFalsy}
            .{then}
                {if}
                    @record
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
                .{ComposerView/messageViewInEditing}
            .{then}
                {ComposerView/updateMessage}
                    @record
                {break}
            {ComposerView/postMessage}
                @record
`;
