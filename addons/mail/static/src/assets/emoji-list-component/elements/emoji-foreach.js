/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            emojiForeach
        [Element/model]
            EmojiListComponent
        [Record/models]
            Foreach
        [Field/target]
            EmojiListComponent:emoji
        [Foreach/collection]
            @record
            .{EmojiListComponent/emojis}
        [EmojiListComponent:emoji/emoji]
            @field
            .{Foreach/get}
                emoji
        [Foreach/as]
            emoji
        [Element/key]
            @field
            .{Foreach/get}
                emoji
            .{Emoji/unicode}
`;
