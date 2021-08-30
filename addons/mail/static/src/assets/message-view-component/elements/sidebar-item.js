/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            sidebarItem
        [Element/model]
            MessageViewComponent
        [web.Element/style]
            [web.scss/margin-left]
                {scss/map-get}
                    {scss/$spacers}
                    1
            [web.scss/margin-right]
                {scss/map-get}
                    {scss/$spacers}
                    1
            {if}
                @record
                .{MessageViewComponent/messageView}
                .{MessageView/isSquashed}
            .{then}
                [web.scss/display]
                    none
`;
