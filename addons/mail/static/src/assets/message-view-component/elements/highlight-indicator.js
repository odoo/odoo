/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            highlightIndicator
        [Element/model]
            MessageViewComponent
        [web.Element/style]
            {web.scss/include}
                {web.scss/o-position-absolute}
                    [$top]
                        0
                    [$left]
                        0
            [web.scss/height]
                100%
            [web.scss/width]
                {scss/$o-mail-discuss-message-highlight-indicator-width}
            [web.scss/transition]
                background-color
                .5s
                ease-out
            {if}
                @record
                .{MessageViewComponent/messageView}
                .{MessageView/isHighlighted}
            .{then}
                [web.scss/background-color]
                    {scss/$o-brand-primary}
`;
