/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Invisible mirrored textarea.
        Used to compute the composer height based on the text content.
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            mirroredTextarea
        [Element/model]
            ComposerTextInputComponent
        [web.Element/tag]
            textarea
        [Record/models]
            ComposerTextInputComponent/textareaStyle
        [web.Element/textContent]
            @record
            .{ComposerTextInputComponent/composerView}
            .{ComposerView/composer}
            .{Composer/textInputContent}
        [web.Element/isDisabled]
            true
        [web.Element/style]
            [web.scss/height]
                0
            [web.scss/position]
                absolute
            [web.scss/opacity]
                0
            [web.scss/overflow]
                hidden
            [web.scss/top]
                -10000
                px
`;
