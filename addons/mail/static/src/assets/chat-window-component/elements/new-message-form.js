/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            newMessageForm
        [Element/model]
            ChatWindowComponent
        [Element/isPresent]
            @record
            .{ChatWindowComponent/chatWindow}
            .{ChatWindow/hasNewMessageForm}
        [web.Element/style]
            [web.scss/padding]
                {scss/map-get}
                    {scss/$spacers}
                    1
            [web.scss/margin-top]
                {scss/map-get}
                    {scss/$spacers}
                    1
            [web.scss/display]
                flex
            [web.scss/align-items]
                center
`;
