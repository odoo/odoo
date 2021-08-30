/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            content
        [Element/model]
            MessageViewComponent
        [web.Element/class]
            mx-2
        [web.Element/style]
            [web.scss/word-wrap]
                break-word
            [web.scss/word-break]
                break-word
            {web.scss/selector}
                [0]
                    *:not(li):not(li div)
                [1]
                    {Dev/comment}
                        Message content can contain arbitrary HTML that might overflow and break
                        the style without this rule.
                        Lists are ignored because otherwise bullet style become hidden from overflow.
                        It's acceptable not to manage overflow of these tags for the moment.
                        It also excludes all div in li because 1st leaf and div child of list overflow
                        may impact the bullet point (at least it does on Safari).
                    [web.scss/max-width]
                        {scss/map-get}
                            {scss/$sizes}
                            100
                    [web.scss/overflow-x]
                        auto
            {web.scss/selector}
                [0]
                    img
                [1]
                    [web.scss/max-width]
                        {scss/map-get}
                            {scss/$sizes}
                            100
                    [web.scss/height]
                        auto
            {web.scss/selector}
                [0]
                    > pre
                [1]
                    [web.scss/white-space]
                        pre-wrap
                    [web.scss/word-break]
                        break-word
            {web.scss/selector}
                [0]
                    .o_mention
                [1]
                    [web.scss/color]
                        {scss/$o-brand-primary}
                    [web.scss/cursor]
                        pointer
            {web.scss/selector}
                [0]
                    .o_mention:hover
                [1]
                    [web.scss/color]
                        {scss/darken}
                            {scss/$o-brand-primary}
                            15%
            {Dev/comment}
                Used to hide buttons on rating emails in chatter
                FIXME: should use a better approach for not having such buttons
                in chatter of such messages, but keep having them in emails.
            {web.scss/selector}
                [0]
                    [summary~="o_mail_notification"]
                [1]
                    [web.scss/display]
                        none
`;
