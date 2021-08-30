/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Called when clicking on attachment button.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            ComposerViewComponent/_onClickAddAttachment
        [Action/params]
            record
                [type]
                    ComposerViewComponent
        [Action/behavior]
            {FileUploader/openBrowserFileUploader}
                @record
                .{ComposerViewComponent/composerView}
                .{ComposerView/fileUploader}
            {if}
                {Device/isMobileDevice}
                .{isFalsy}
            .{then}
                {Record/update}
                    [0]
                        @record
                        .{ComposerViewComponent/composerView}
                    [1]
                        [ComposerView/doFocus]
                            true
`;
