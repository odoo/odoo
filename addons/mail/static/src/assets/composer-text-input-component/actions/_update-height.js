/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Updates the textarea height.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            ComposerTextInputComponent/_updateHeight
        [Action/params]
            record
        [Action/behavior]
            {Record/update}
                [0]
                    @record
                    .{ComposerTextInputComponent/mirroredTextarea}
                [1]
                    [web.Element/value]
                        @record
                        .{ComposerTextInputComponent/composerView}
                        .{ComposerView/composer}
                        .{Composer/textInputContent}
            {Record/update}
                [0]
                    @record
                    .{ComposerTextInputComponent/textarea}
                    .{web.Element/style}
                [1]
                    [web.scss/height]
                        @record
                        .{ComposerTextInputComponent/mirroredTextarea}
                        .{web.Element/scrollHeight}
                        .{+}
                            px
`;
