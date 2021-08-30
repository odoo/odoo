/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            listItem
        [Element/model]
            ChatWindowHiddenMenuComponent
        [Record/models]
            Foreach
        [Foreach/collection]
            {ChatWindowManager/allOrderedHidden}
        [Foreach/as]
            chatWindow
        [Element/key]
            @field
            .{Foreach/get}
                chatWindow
            .{Record/id}
        [Field/target]
            ChatWindowHiddenMenuComponent:listItem
        [ChatWindowHiddenMenuComponent:listItem/chatWindow]
            @field
            .{Foreach/get}
                chatWindow
`;
