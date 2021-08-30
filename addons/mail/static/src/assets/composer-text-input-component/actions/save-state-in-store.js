/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Saves the composer text input state in store
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            ComposerTextInputComponent/saveStateInStore
        [Action/params]
            record
        [Action/behavior]
            {Record/update}
                [0]
                    @record
                    .{ComposerTextInputComponent/composerView}
                    .{ComposerView/composer}
                [1]
                    [Composer/textInputContent]
                        @record
                        .{ComposerTextInputComponent/textarea}
                        .{web.Element/value}
                    [Composer/textInputCursorEnd]
                        @record
                        .{ComposerTextInputComponent/textarea}
                        .{web.Element/selectionEnd}
                    [Composer/textInputCursorStart]
                        @record
                        .{ComposerTextInputComponent/textarea}
                        .{web.Element/selectionStart}
                    [Composer/textInputSelectionDirection]
                        @record
                        .{ComposerTextInputComponent/textarea}
                        .{web.Element/selectionDirection}
`;
