/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            sidebar
        [Element/model]
            MessageViewComponent
        [web.Element/class]
            align-items-start
        [web.Element/style]
            [web.scss/flex]
                0
                0
                {scss/$o-mail-message-sidebar-width}
            [web.scss/max-width]
                {scss/$o-mail-message-sidebar-width}
            [web.scss/display]
                flex
            [web.scss/margin-inline-end]
                {scss/map-get}
                    {scss/$spacers}
                    2
            [web.scss/justify-content]
                center
            {if}
                @record
                .{MessageViewComponent/messageView}
                .{MessageView/isSquashed}
            .{then}
                [web.scss/align-items]
                    flex-start
`;
