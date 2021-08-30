/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            textareaStyle
        [Element/model]
            ComposerTextInputComponent
        [web.Element/style]
            [web.scss/padding]
                10
                px
                {Dev/comment}
                    carefully crafted to have the text in the middle in chat window
            [web.scss/min-height]
                40
                px
            [web.scss/resize]
                none
            [web.scss/border-radius]
                {scss/$o-mail-rounded-rectangle-border-radius-lg}
            [web.scss/border]
                none
            [web.scss/overflow]
                auto
            {web.scss/selector}
                [0]
                    &::placeholder
                [1]
                    {scss/include}
                        {scss/text-truncate}
            {if}
                @record
                .{ComposerTextInputComponent/isCompact}
            .{then}
                {Dev/comment}
                    When composer is compact, textarea should not be rounded on the right as
                    buttons are glued to it
                [web.scss/border-top-right-radius]
                    0
                [web.scss/border-bottom-right-radius]
                    0
                {Dev/comment}
                    Chat window height should be taken into account to choose this value
                    ideally this should be less than the third of chat window height
                [web.scss/max-height]
                    100
                    px
            {if}
                @record
                .{ComposerTextInputComponent/isCompact}
            .{then}
                {Dev/comment}
                    Don't allow the input to take the whole height when it's not compact
                    (like in chatter for example) but allow it to take some more place
                [web.scss/max-height]
                    400
                    px
`;
