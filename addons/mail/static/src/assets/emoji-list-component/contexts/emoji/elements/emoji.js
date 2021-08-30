/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            emoji
        [Element/model]
            EmojiListComponent:emoji
        [web.Element/tag]
            span
        [Element/onClick]
            {EmojiListView/onClickEmoji}
                [0]
                    @record
                    .{EmojiListComponent/emojiListView}
                [1]
                    @ev
        [web.Element/title]
            @record
            .{EmojiListComponent:emoji/emoji}
            .{Emoji/description}
        [web.Element/data-source]
            @record
            .{EmojiListComponent:emoji/emoji}
            .{Emoji/sources}
            .{Collection/first}
        [web.Element/data-unicode]
            @record
            .{EmojiListComponent:emoji/emoji}
            .{Emoji/unicode}
        [web.Element/textContent]
            @record
            .{EmojiListComponent:emoji/emoji}
            .{Emoji/unicode}
        [web.Element/style]
            [web.scss/font-size]
                1.1
                em
            [web.scss/margin]
                {scss/map-get}
                    {scss/$spacers}
                    1
            [web.scss/cursor]
                pointer
`;
