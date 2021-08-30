/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            icon
        [Element/model]
            ChatWindowHeaderComponent
        [Field/target]
            ThreadIconComponent
        [Record/models]
            ChatWindowHeaderComponent/item
        [Element/isPresent]
            @record
            .{ChatWindowHeaderComponent/chatWindow}
            .{ChatWindow/thread}
            .{&}
                @record
                .{ChatWindowHeaderComponent/chatWindow}
                .{ChatWindow/thread}
                .{Thread/model}
                .{=}
                    mail.channel
        [ThreadIconComponent/thread]
            @record
            .{ChatWindowHeaderComponent/chatWindow}
            .{ChatWindow/thread}
`;
